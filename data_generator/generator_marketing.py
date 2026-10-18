import argparse
import csv
import os
import random
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Set, Tuple

from google.cloud import bigquery
from google.cloud import storage


DEFAULT_PROJECT_ID = "data-mesh-marketing"
DEFAULT_DATASET = "marketing_raw"
DEFAULT_BUCKET = "data-mesh-marketing-project3-bucket"
DEFAULT_INVENTORY_TABLE = "publishing-mesh-logistics.logistics_products.inventory_by_book"
DEFAULT_CAMPAIGNS_TABLE = "data-mesh-marketing.marketing_raw.ext_marketing_campaigns"
DEFAULT_METRICS_TABLE = "data-mesh-marketing.marketing_raw.ext_marketing_campaign_daily_metrics"

CHANNELS = ["google_ads", "facebook_ads", "email", "instagram", "youtube", "affiliate"]
OBJECTIVES = ["awareness", "traffic", "conversion", "retention"]
SEGMENTS = ["students", "parents", "business", "fiction_readers", "nonfiction_readers", "young_adults"]
PROMO_TYPES = ["homepage_feature", "newsletter_feature", "bundle_promo"]
SOURCE_SYSTEM = "marketing_generator_cli"
OWNER_TEAM = "marketing"

CAMPAIGN_NAME_PREFIXES = [
    "spring", "summer", "autumn", "winter", "bestseller", "new_release",
    "weekend", "reading", "back_to_school", "holiday", "spotlight", "top_picks"
]
CAMPAIGN_NAME_SUFFIXES = [
    "push", "promo", "campaign", "feature", "boost", "selection"
]


@dataclass
class Book:
    book_id: int


@dataclass
class ExistingCampaign:
    campaign_id: int
    start_date: date
    end_date: date
    budget_amount: Decimal


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate marketing data and upload CSV files to GCS.\n"
            "\n"
            "Logika per load_date:\n"
            "  - Źródło książek: inventory_by_book gdzie snapshot_date = load_date - 1\n"
            "    i total_stock_available > 0 (tylko dostępne w magazynie)\n"
            "  - Zawsze: nowe kampanie (co najmniej 1 aktywna na load_date)\n"
            "  - Produkty: tylko kampanie z start_date == load_date\n"
            "  - Metryki: wszystkie aktywne kampanie, bez duplikatów\n"
        )
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--inventory-table", default=DEFAULT_INVENTORY_TABLE)
    parser.add_argument("--campaigns-table", default=DEFAULT_CAMPAIGNS_TABLE)
    parser.add_argument("--metrics-table", default=DEFAULT_METRICS_TABLE)
    parser.add_argument("--load-date", required=True, help="Load date in YYYY-MM-DD format")
    parser.add_argument("--num-campaigns", type=int, default=4)
    parser.add_argument("--books-min", type=int, default=20)
    parser.add_argument("--books-max", type=int, default=80)
    parser.add_argument("--random-seed", type=int, default=None)
    parser.add_argument("--gcs-prefix", default="marketing")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def decimal_2(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_bigquery_client(project_id: str) -> bigquery.Client:
    return bigquery.Client(project=project_id)


def get_storage_client(project_id: str) -> storage.Client:
    return storage.Client(project=project_id)


def daterange(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


# ---------------------------------------------------------------------------
# BigQuery reads
# ---------------------------------------------------------------------------

def get_max_campaign_id(client: bigquery.Client, campaigns_table: str) -> int:
    query = f"""
    SELECT COALESCE(MAX(campaign_id), 0) AS max_campaign_id
    FROM `{campaigns_table}`
    """
    try:
        rows = list(client.query(query).result())
        return int(rows[0].max_campaign_id) if rows else 0
    except Exception:
        return 0


def load_available_books(
    client: bigquery.Client,
    inventory_table: str,
    load_date: date
) -> List[Book]:
    """
    Pobiera book_id dostępnych w magazynie na dzień poprzedni względem load_date.
    Filtr: snapshot_date = load_date - 1 AND total_stock_available > 0.
    Używamy load_date - 1 bo snapshot z bieżącego dnia może jeszcze nie istnieć.
    """
    snapshot_date = (load_date - timedelta(days=1)).isoformat()
    query = f"""
    SELECT DISTINCT book_id
    FROM `{inventory_table}`
    WHERE snapshot_date = DATE('{snapshot_date}')
      AND total_stock_available > 0
      AND book_id IS NOT NULL
    """
    try:
        rows = list(client.query(query).result())
        books = [Book(book_id=int(row.book_id)) for row in rows]
    except Exception as e:
        raise RuntimeError(f"Could not load inventory data: {e}")

    if not books:
        raise ValueError(
            f"No books with total_stock_available > 0 found in inventory "
            f"for snapshot_date={snapshot_date}. "
            f"Cannot generate campaign products."
        )
    return books


def load_active_campaigns(
    client: bigquery.Client,
    campaigns_table: str,
    load_date: date
) -> List[ExistingCampaign]:
    """Kampanie aktywne na load_date: start_date <= load_date <= end_date."""
    query = f"""
    SELECT campaign_id, start_date, end_date, budget_amount
    FROM `{campaigns_table}`
    WHERE start_date <= DATE('{load_date.isoformat()}')
      AND end_date   >= DATE('{load_date.isoformat()}')
    """
    try:
        rows = list(client.query(query).result())
        return [
            ExistingCampaign(
                campaign_id=int(row.campaign_id),
                start_date=row.start_date,
                end_date=row.end_date,
                budget_amount=Decimal(str(row.budget_amount))
            )
            for row in rows
        ]
    except Exception as e:
        print(f"[WARN] Could not load active campaigns: {e}")
        return []


def load_existing_metric_pairs(
    client: bigquery.Client,
    metrics_table: str,
    campaign_ids: List[int],
    load_date: date
) -> Set[Tuple[int, str]]:
    """Istniejące (campaign_id, event_date) — guard przed duplikatami przy rerunach."""
    if not campaign_ids:
        return set()
    ids_str = ", ".join(str(i) for i in campaign_ids)
    query = f"""
    SELECT DISTINCT campaign_id, CAST(event_date AS STRING) AS event_date
    FROM `{metrics_table}`
    WHERE campaign_id IN ({ids_str})
      AND event_date <= DATE('{load_date.isoformat()}')
    """
    try:
        rows = list(client.query(query).result())
        return {(int(row.campaign_id), row.event_date) for row in rows}
    except Exception as e:
        print(f"[WARN] Could not load existing metric pairs: {e}")
        return set()


# ---------------------------------------------------------------------------
# Generators — kampanie
# ---------------------------------------------------------------------------

def build_campaign_name(load_date: date, idx: int) -> str:
    prefix = random.choice(CAMPAIGN_NAME_PREFIXES)
    suffix = random.choice(CAMPAIGN_NAME_SUFFIXES)
    return f"{prefix}_{suffix}_{load_date.strftime('%Y%m%d')}_{idx}"


def generate_campaign_dates(load_date: date, force_start_today: bool = False) -> Tuple[date, date]:
    """
    force_start_today=True  → start_date == load_date (gwarantuje aktywność i generowanie produktów)
    force_start_today=False → start_date = load_date + 0..3 dni (może być planned)
    """
    if force_start_today:
        start_date = load_date
    else:
        start_offset = random.randint(0, 3)
        start_date = load_date + timedelta(days=start_offset)
    duration_days = random.randint(7, 28)
    end_date = start_date + timedelta(days=duration_days)
    return start_date, end_date


def generate_campaigns(
    load_date: date,
    start_campaign_id: int,
    num_campaigns: int,
    source_file: str
) -> List[Dict]:
    """
    Pierwsza kampania (i=0) zawsze startuje na load_date — gwarantuje
    co najmniej 1 aktywną kampanię i co najmniej 1 plik products per run.
    """
    campaigns = []
    for i in range(num_campaigns):
        campaign_id = start_campaign_id + i + 1
        force_today = (i == 0)
        start_date, end_date = generate_campaign_dates(load_date, force_start_today=force_today)
        budget_amount = decimal_2(random.uniform(1500, 15000))
        status = "planned" if start_date > load_date else "active"
        campaigns.append({
            "campaign_id": campaign_id,
            "campaign_name": build_campaign_name(load_date, i + 1),
            "channel": random.choice(CHANNELS),
            "objective": random.choice(OBJECTIVES),
            "target_segment": random.choice(SEGMENTS),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "budget_amount": str(budget_amount),
            "status": status,
            "owner_team": OWNER_TEAM,
            "load_date": load_date.isoformat(),
            "source_file": source_file
        })
    return campaigns


# ---------------------------------------------------------------------------
# Generators — produkty (tylko przy start_date == load_date)
# ---------------------------------------------------------------------------

def generate_campaign_products(
    campaigns: List[Dict],
    books: List[Book],
    books_min: int,
    books_max: int,
    load_date: date,
    source_file: str
) -> List[Dict]:
    """
    Generuje produkty TYLKO dla kampanii których start_date == load_date.
    Książki pochodzą z inventory_by_book (snapshot_date = load_date - 1,
    total_stock_available > 0) — marketing promuje tylko dostępne pozycje.
    """
    rows = []
    max_pick = min(books_max, len(books))
    min_pick = min(books_min, max_pick)

    starting_today = [
        c for c in campaigns
        if date.fromisoformat(c["start_date"]) == load_date
    ]

    for campaign in starting_today:
        campaign_id = int(campaign["campaign_id"])
        picked_books = random.sample(books, random.randint(min_pick, max_pick))
        for book in picked_books:
            rows.append({
                "campaign_id": campaign_id,
                "book_id": book.book_id,
                "promo_type": random.choice(PROMO_TYPES),
                "featured_flag": random.random() < 0.15,
                "load_date": load_date.isoformat(),
                "source_file": source_file
            })

    return rows


# ---------------------------------------------------------------------------
# Generators — daily metrics
# ---------------------------------------------------------------------------

def _build_metric_row(
    campaign_id: int,
    event_date: date,
    daily_budget_cap: Decimal,
    load_date: date,
    source_file: str
) -> Dict:
    impressions = random.randint(2000, 50000)
    ctr = random.uniform(0.01, 0.09)
    clicks = int(impressions * ctr)
    sessions = max(clicks - random.randint(0, max(1, clicks // 10)), 0)
    add_to_cart = random.randint(0, max(1, sessions // 5))
    cost_amount = decimal_2(
        min(float(daily_budget_cap), random.uniform(50, float(daily_budget_cap)))
    )
    return {
        "campaign_id": campaign_id,
        "event_date": event_date.isoformat(),
        "impressions": impressions,
        "clicks": clicks,
        "cost_amount": str(cost_amount),
        "sessions": sessions,
        "add_to_cart": add_to_cart,
        "source_system": SOURCE_SYSTEM,
        "load_date": load_date.isoformat(),
        "source_file": source_file
    }


def generate_campaign_daily_metrics(
    campaigns: List[Dict],
    active_existing: List[ExistingCampaign],
    load_date: date,
    source_file: str,
    existing_metric_pairs: Set[Tuple[int, str]]
) -> List[Dict]:
    """
    Generuje daily metrics dla nowych kampanii i aktywnych istniejących.
    Nie generuje przyszłości (max event_date = load_date).
    Pomija pary już obecne w BQ (idempotencja przy rerunach).
    """
    rows = []

    new_as_existing = [
        ExistingCampaign(
            campaign_id=int(c["campaign_id"]),
            start_date=date.fromisoformat(c["start_date"]),
            end_date=date.fromisoformat(c["end_date"]),
            budget_amount=Decimal(c["budget_amount"])
        )
        for c in campaigns
    ]

    for ec in new_as_existing + active_existing:
        total_days = (ec.end_date - ec.start_date).days + 1
        daily_budget_cap = (ec.budget_amount / Decimal(total_days)).quantize(Decimal("0.01"))
        effective_end = min(ec.end_date, load_date)

        for event_date in daterange(ec.start_date, effective_end):
            key = (ec.campaign_id, event_date.isoformat())
            if key in existing_metric_pairs:
                continue
            rows.append(_build_metric_row(
                campaign_id=ec.campaign_id,
                event_date=event_date,
                daily_budget_cap=daily_budget_cap,
                load_date=load_date,
                source_file=source_file
            ))
            existing_metric_pairs.add(key)

    return rows


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def write_csv(path: str, rows: List[Dict], fieldnames: List[str]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def upload_outputs(
    storage_client: storage.Client,
    bucket_name: str,
    local_files: Dict[str, str],
    gcs_prefix: str,
    load_date: str
) -> Dict[str, str]:
    """
    Ścieżka GCS: <prefix>/<table>/load_date=YYYY-MM-DD/<table>_YYYY-MM-DD.csv
    Idempotentna — rerun tego samego load_date nadpisuje ten sam plik.
    """
    uploaded = {}
    for table_name, local_path in local_files.items():
        filename = os.path.basename(local_path)
        object_name = f"{gcs_prefix}/{table_name}/load_date={load_date}/{filename}"
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.upload_from_filename(local_path)
        uploaded[table_name] = f"gs://{bucket_name}/{object_name}"
    return uploaded


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    if args.books_min < 1:
        raise ValueError("--books-min must be >= 1")
    if args.books_max < args.books_min:
        raise ValueError("--books-max must be >= --books-min")
    if args.num_campaigns < 1:
        raise ValueError("--num-campaigns must be >= 1")

    load_date = date.fromisoformat(args.load_date)
    snapshot_date = load_date - timedelta(days=1)

    if args.random_seed is not None:
        random.seed(args.random_seed)

    bq_client = get_bigquery_client(args.project_id)
    storage_client = get_storage_client(args.project_id)

    # -----------------------------------------------------------------------
    # 1. Dane referencyjne
    # -----------------------------------------------------------------------
    print(f"[1/5] Loading available books from inventory (snapshot_date={snapshot_date})...")
    books = load_available_books(bq_client, args.inventory_table, load_date)
    print(f"      Books with stock available: {len(books)}")

    print(f"[2/5] Reading current max campaign_id from {args.campaigns_table}...")
    max_campaign_id = get_max_campaign_id(bq_client, args.campaigns_table)
    print(f"      Current max campaign_id: {max_campaign_id}")

    print(f"[3/5] Loading active campaigns for load_date={load_date}...")
    active_campaigns = load_active_campaigns(bq_client, args.campaigns_table, load_date)
    print(f"      Active existing campaigns: {len(active_campaigns)}")

    # -----------------------------------------------------------------------
    # 2. Guard przed duplikatami metryk
    # -----------------------------------------------------------------------
    new_campaign_ids_preview = list(range(
        max_campaign_id + 1,
        max_campaign_id + args.num_campaigns + 1
    ))
    all_campaign_ids = (
        [ec.campaign_id for ec in active_campaigns] + new_campaign_ids_preview
    )

    print(f"[4/5] Loading existing metric pairs from {args.metrics_table}...")
    existing_metric_pairs = load_existing_metric_pairs(
        bq_client, args.metrics_table, all_campaign_ids, load_date
    )
    print(f"      Existing metric pairs: {len(existing_metric_pairs)}")

    # -----------------------------------------------------------------------
    # 3. Generowanie
    # -----------------------------------------------------------------------
    print("[5/5] Generating data...")
    with tempfile.TemporaryDirectory() as tmpdir:
        campaigns_filename = f"marketing_campaigns_{args.load_date}.csv"
        products_filename  = f"marketing_campaign_products_{args.load_date}.csv"
        metrics_filename   = f"marketing_campaign_daily_metrics_{args.load_date}.csv"

        campaigns = generate_campaigns(
            load_date=load_date,
            start_campaign_id=max_campaign_id,
            num_campaigns=args.num_campaigns,
            source_file=campaigns_filename
        )

        products = generate_campaign_products(
            campaigns=campaigns,
            books=books,
            books_min=args.books_min,
            books_max=args.books_max,
            load_date=load_date,
            source_file=products_filename
        )

        metrics = generate_campaign_daily_metrics(
            campaigns=campaigns,
            active_existing=active_campaigns,
            load_date=load_date,
            source_file=metrics_filename,
            existing_metric_pairs=existing_metric_pairs
        )

        # -----------------------------------------------------------------------
        # 4. Zapis CSV
        # -----------------------------------------------------------------------
        local_campaigns = os.path.join(tmpdir, campaigns_filename)
        local_products  = os.path.join(tmpdir, products_filename)
        local_metrics   = os.path.join(tmpdir, metrics_filename)

        write_csv(local_campaigns, campaigns, [
            "campaign_id", "campaign_name", "channel", "objective", "target_segment",
            "start_date", "end_date", "budget_amount", "status", "owner_team",
            "load_date", "source_file"
        ])
        write_csv(local_products, products, [
            "campaign_id", "book_id", "promo_type", "featured_flag",
            "load_date", "source_file"
        ])
        write_csv(local_metrics, metrics, [
            "campaign_id", "event_date", "impressions", "clicks", "cost_amount",
            "sessions", "add_to_cart", "source_system",
            "load_date", "source_file"
        ])

        # -----------------------------------------------------------------------
        # 5. Asercje przed uploadem
        # -----------------------------------------------------------------------
        campaign_ids_in_batch = [c["campaign_id"] for c in campaigns]
        assert len(campaign_ids_in_batch) == len(set(campaign_ids_in_batch)), \
            "FATAL: duplicate campaign_id in generated campaigns!"

        product_pairs_in_batch = [(r["campaign_id"], r["book_id"]) for r in products]
        assert len(product_pairs_in_batch) == len(set(product_pairs_in_batch)), \
            "FATAL: duplicate (campaign_id, book_id) in generated products!"

        metric_pairs_in_batch = [(r["campaign_id"], r["event_date"]) for r in metrics]
        assert len(metric_pairs_in_batch) == len(set(metric_pairs_in_batch)), \
            "FATAL: duplicate (campaign_id, event_date) in generated metrics!"

        active_in_batch = [c for c in campaigns if c["status"] == "active"]
        assert len(active_in_batch) >= 1, \
            "FATAL: no active campaigns generated for this load_date!"

        # -----------------------------------------------------------------------
        # 6. Upload GCS
        # -----------------------------------------------------------------------
        local_files_to_upload: Dict[str, str] = {
            "marketing_campaigns": local_campaigns,
            "marketing_campaign_daily_metrics": local_metrics,
        }
        if products:
            local_files_to_upload["marketing_campaign_products"] = local_products

        uploaded = upload_outputs(
            storage_client=storage_client,
            bucket_name=args.bucket,
            local_files=local_files_to_upload,
            gcs_prefix=args.gcs_prefix,
            load_date=args.load_date
        )

    # -----------------------------------------------------------------------
    # Podsumowanie
    # -----------------------------------------------------------------------
    starting_today = sum(
        1 for c in campaigns
        if date.fromisoformat(c["start_date"]) == load_date
    )
    print()
    print("=" * 60)
    print("Generation completed successfully.")
    print(f"  Inventory snapshot_date         : {snapshot_date}")
    print(f"  Books available in stock        : {len(books)}")
    print(f"  New campaigns generated         : {len(campaigns)}")
    print(f"  Campaigns starting today        : {starting_today}")
    print(f"  Product rows generated          : {len(products)}")
    print(f"  Active existing campaigns       : {len(active_campaigns)}")
    print(f"  Daily metric rows generated     : {len(metrics)}")
    print()
    print("Uploaded files:")
    for table_name, gcs_path in uploaded.items():
        print(f"  {table_name}:")
        print(f"    {gcs_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()