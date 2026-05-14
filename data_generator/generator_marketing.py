import argparse
import csv
import os
import random
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple

from google.cloud import bigquery
from google.cloud import storage


DEFAULT_PROJECT_ID = "data-mesh-marketing"
DEFAULT_DATASET = "marketing_raw"
DEFAULT_BUCKET = "data-mesh-marketing-project3-bucket"
DEFAULT_CATALOG_TABLE = "publishing-mesh-project.catalog.books"
DEFAULT_CAMPAIGNS_TABLE = "data-mesh-marketing.marketing_raw.marketing_campaigns"

CHANNELS = ["google_ads", "facebook_ads", "email", "instagram", "youtube", "affiliate"]
OBJECTIVES = ["awareness", "traffic", "conversion", "retention"]
SEGMENTS = ["students", "parents", "business", "fiction_readers", "nonfiction_readers", "young_adults"]
PROMO_TYPES = ["discount", "homepage_feature", "newsletter_feature", "bundle_promo"]
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
    title: str
    category: str
    format: str
    list_price: Decimal


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate marketing data, upload CSV files to GCS, later load them to BigQuery."
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--catalog-table", default=DEFAULT_CATALOG_TABLE)
    parser.add_argument("--campaigns-table", default=DEFAULT_CAMPAIGNS_TABLE)
    parser.add_argument("--load-date", required=True, help="Load date in YYYY-MM-DD format")
    parser.add_argument("--num-campaigns", type=int, default=4, help="Number of new campaigns to generate")
    parser.add_argument("--books-min", type=int, default=20)
    parser.add_argument("--books-max", type=int, default=80)
    parser.add_argument("--random-seed", type=int, default=None)
    parser.add_argument("--gcs-prefix", default="marketing")
    return parser.parse_args()


def decimal_2(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_bigquery_client(project_id: str) -> bigquery.Client:
    return bigquery.Client(project=project_id)


def get_storage_client(project_id: str) -> storage.Client:
    return storage.Client(project=project_id)


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


def load_catalog_books(client: bigquery.Client, catalog_table: str) -> List[Book]:
    query = f"""
    SELECT
      book_id,
      title,
      category,
      format,
      list_price
    FROM `{catalog_table}`
    WHERE book_id IS NOT NULL
    """
    rows = client.query(query).result()
    books = []
    for row in rows:
        price = row.list_price if row.list_price is not None else Decimal("29.99")
        books.append(
            Book(
                book_id=int(row.book_id),
                title=row.title or "unknown_title",
                category=(row.category or "unknown").lower().replace(" ", "_"),
                format=(row.format or "unknown").lower().replace(" ", "_"),
                list_price=Decimal(str(price))
            )
        )
    if not books:
        raise ValueError("No books found in catalog table.")
    return books


def build_campaign_name(load_date: date, idx: int) -> str:
    prefix = random.choice(CAMPAIGN_NAME_PREFIXES)
    suffix = random.choice(CAMPAIGN_NAME_SUFFIXES)
    return f"{prefix}_{suffix}_{load_date.strftime('%Y%m%d')}_{idx}"


def generate_campaign_dates(load_date: date) -> Tuple[date, date]:
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
    campaigns = []
    generated_at = datetime.utcnow().isoformat(timespec="seconds")

    for i in range(num_campaigns):
        campaign_id = start_campaign_id + i + 1
        start_date, end_date = generate_campaign_dates(load_date)
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
            "generated_at": generated_at,
            "source_file": source_file
        })
    return campaigns


def generate_campaign_products(
    campaigns: List[Dict],
    books: List[Book],
    books_min: int,
    books_max: int,
    source_file: str
) -> List[Dict]:
    generated_at = datetime.utcnow().isoformat(timespec="seconds")
    rows = []

    max_pick = min(books_max, len(books))
    min_pick = min(books_min, max_pick)

    for campaign in campaigns:
        picked_books = random.sample(books, random.randint(min_pick, max_pick))
        for book in picked_books:
            discount_pct = random.choice([5, 10, 15, 20, 25, 30, None])
            promo_type = random.choice(PROMO_TYPES)
            featured_flag = random.random() < 0.15

            if discount_pct:
                promo_price = (book.list_price * Decimal(100 - discount_pct) / Decimal(100)).quantize(Decimal("0.01"))
            else:
                promo_price = book.list_price.quantize(Decimal("0.01"))

            rows.append({
                "campaign_id": campaign["campaign_id"],
                "book_id": book.book_id,
                "promo_type": promo_type,
                "discount_pct": discount_pct,
                "featured_flag": featured_flag,
                "promo_price": str(promo_price),
                "load_date": campaign["load_date"],
                "generated_at": generated_at,
                "source_file": source_file
            })
    return rows


def daterange(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def generate_campaign_daily_metrics(
    campaigns: List[Dict],
    source_file: str
) -> List[Dict]:
    generated_at = datetime.utcnow().isoformat(timespec="seconds")
    rows = []

    for campaign in campaigns:
        start_date = date.fromisoformat(campaign["start_date"])
        end_date = date.fromisoformat(campaign["end_date"])
        budget = Decimal(campaign["budget_amount"])

        total_days = (end_date - start_date).days + 1
        daily_budget_cap = (budget / Decimal(total_days)).quantize(Decimal("0.01"))

        for event_date in daterange(start_date, end_date):
            impressions = random.randint(2000, 50000)
            ctr = random.uniform(0.01, 0.09)
            clicks = int(impressions * ctr)
            sessions = max(clicks - random.randint(0, max(1, clicks // 10)), 0)
            add_to_cart = random.randint(0, max(1, sessions // 5))
            conversions = random.randint(0, max(1, add_to_cart))
            cost_amount = decimal_2(min(float(daily_budget_cap), random.uniform(50, float(daily_budget_cap))))

            rows.append({
                "campaign_id": campaign["campaign_id"],
                "event_date": event_date.isoformat(),
                "impressions": impressions,
                "clicks": clicks,
                "cost_amount": str(cost_amount),
                "sessions": sessions,
                "add_to_cart": add_to_cart,
                "conversions": conversions,
                "source_system": SOURCE_SYSTEM,
                "load_date": campaign["load_date"],
                "generated_at": generated_at,
                "source_file": source_file
            })
    return rows


def write_csv(path: str, rows: List[Dict], fieldnames: List[str]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def upload_file_to_gcs(storage_client: storage.Client, bucket_name: str, local_path: str, object_name: str):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_path)


def upload_outputs(
    storage_client: storage.Client,
    bucket_name: str,
    local_files: Dict[str, str],
    gcs_prefix: str,
    load_date: str
):
    uploaded = {}
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for table_name, local_path in local_files.items():
        filename = os.path.basename(local_path)
        object_name = f"{gcs_prefix}/{table_name}/load_date={load_date}/{timestamp}_{filename}"
        upload_file_to_gcs(storage_client, bucket_name, local_path, object_name)
        uploaded[table_name] = f"gs://{bucket_name}/{object_name}"
    return uploaded


def main():
    args = parse_args()

    if args.books_min < 1:
        raise ValueError("--books-min must be >= 1")
    if args.books_max < args.books_min:
        raise ValueError("--books-max must be >= --books-min")
    if args.num_campaigns < 1:
        raise ValueError("--num-campaigns must be >= 1")

    load_date = date.fromisoformat(args.load_date)

    if args.random_seed is not None:
        random.seed(args.random_seed)

    bq_client = get_bigquery_client(args.project_id)
    storage_client = get_storage_client(args.project_id)

    print(f"Loading catalog books from {args.catalog_table}...")
    books = load_catalog_books(bq_client, args.catalog_table)
    print(f"Loaded {len(books)} books from catalog.")

    print(f"Reading current max campaign_id from {args.campaigns_table}...")
    max_campaign_id = get_max_campaign_id(bq_client, args.campaigns_table)
    print(f"Current max campaign_id: {max_campaign_id}")

    with tempfile.TemporaryDirectory() as tmpdir:
        source_suffix = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        campaigns_file = f"marketing_campaigns_{args.load_date}_{source_suffix}.csv"
        products_file = f"marketing_campaign_products_{args.load_date}_{source_suffix}.csv"
        metrics_file = f"marketing_campaign_daily_metrics_{args.load_date}_{source_suffix}.csv"

        campaigns = generate_campaigns(
            load_date=load_date,
            start_campaign_id=max_campaign_id,
            num_campaigns=args.num_campaigns,
            source_file=campaigns_file
        )

        products = generate_campaign_products(
            campaigns=campaigns,
            books=books,
            books_min=args.books_min,
            books_max=args.books_max,
            source_file=products_file
        )

        metrics = generate_campaign_daily_metrics(
            campaigns=campaigns,
            source_file=metrics_file
        )

        local_campaigns = os.path.join(tmpdir, campaigns_file)
        local_products = os.path.join(tmpdir, products_file)
        local_metrics = os.path.join(tmpdir, metrics_file)

        write_csv(
            local_campaigns,
            campaigns,
            [
                "campaign_id", "campaign_name", "channel", "objective", "target_segment",
                "start_date", "end_date", "budget_amount", "status", "owner_team",
                "load_date", "generated_at", "source_file"
            ]
        )

        write_csv(
            local_products,
            products,
            [
                "campaign_id", "book_id", "promo_type", "discount_pct", "featured_flag",
                "promo_price", "load_date", "generated_at", "source_file"
            ]
        )

        write_csv(
            local_metrics,
            metrics,
            [
                "campaign_id", "event_date", "impressions", "clicks", "cost_amount",
                "sessions", "add_to_cart", "conversions", "source_system",
                "load_date", "generated_at", "source_file"
            ]
        )

        uploaded = upload_outputs(
            storage_client=storage_client,
            bucket_name=args.bucket,
            local_files={
                "marketing_campaigns": local_campaigns,
                "marketing_campaign_products": local_products,
                "marketing_campaign_daily_metrics": local_metrics
            },
            gcs_prefix=args.gcs_prefix,
            load_date=args.load_date
        )

        print("Generation completed successfully.")
        print(f"Generated campaigns: {len(campaigns)}")
        print(f"Generated campaign_products: {len(products)}")
        print(f"Generated campaign_daily_metrics: {len(metrics)}")
        print("Uploaded files:")
        for table_name, gcs_path in uploaded.items():
            print(f"  - {table_name}: {gcs_path}")


if __name__ == "__main__":
    main()