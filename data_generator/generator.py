import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
if BASE_DIR.name != "gcp_project3":
    raise RuntimeError(
        "Skrypt musi znajdować się w strukturze gcp_project3/data_generator/generator.py"
    )

CATALOG_DIR = BASE_DIR / "catalog"
SALES_DIR = BASE_DIR / "sales"
LOGISTICS_DIR = BASE_DIR / "logistics"
MARKETING_DIR = BASE_DIR / "marketing"
SHARED_DIR = BASE_DIR / "shared"


def validate_directories() -> None:
    required_dirs = [CATALOG_DIR, SALES_DIR, LOGISTICS_DIR, MARKETING_DIR, SHARED_DIR]
    missing_dirs = [str(directory) for directory in required_dirs if not directory.exists()]
    if missing_dirs:
        raise FileNotFoundError(
            "Brakuje wymaganych folderów: " + ", ".join(missing_dirs)
        )


def random_date(start: date, end: date) -> date:
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def weighted_choice(options):
    values = [item[0] for item in options]
    weights = [item[1] for item in options]
    return random.choices(values, weights=weights, k=1)[0]


def generate_isbn(existing_isbns: set[str]) -> str:
    while True:
        isbn = "978" + "".join(str(random.randint(0, 9)) for _ in range(10))
        if isbn not in existing_isbns:
            existing_isbns.add(isbn)
            return isbn


def generate_books(num_books: int) -> list[dict]:
    adjectives = [
        "Hidden", "Lost", "Silent", "Dark", "Golden", "Secret", "Broken",
        "Last", "Forgotten", "Endless", "Burning", "Lonely", "Crystal"
    ]
    nouns = [
        "River", "Empire", "Garden", "Letter", "Forest", "Promise", "House",
        "Storm", "Crown", "Shadow", "Library", "Path", "Dream"
    ]
    authors = [
        "Anna Kowalska", "Jan Nowak", "Maria Zielinska", "Piotr Wisniewski",
        "Katarzyna Wrobel", "Tomasz Lewandowski", "Julia Mazur",
        "Michal Dabrowski", "Alicja Szymanska", "Pawel Kaczmarek"
    ]
    publishers = [
        "Amber Press", "Nova Books", "Blue Ink Publishing",
        "Open Chapter House", "Starlight Editions"
    ]
    categories = [
        "Fiction", "Fantasy", "Science", "History", "Romance",
        "Crime", "Children", "Business"
    ]
    formats = [
        ("paper", 60),
        ("ebook", 25),
        ("audiobook", 15),
    ]

    books = []
    existing_titles = set()
    existing_isbns = set()

    for book_id in range(1, num_books + 1):
        while True:
            title = f"The {random.choice(adjectives)} {random.choice(nouns)}"
            if title not in existing_titles:
                existing_titles.add(title)
                break

        book = {
            "book_id": book_id,
            "isbn": generate_isbn(existing_isbns),
            "title": title,
            "author_name": random.choice(authors),
            "publisher_name": random.choice(publishers),
            "category": random.choice(categories),
            "format": weighted_choice(formats),
            "publication_date": random_date(date(2018, 1, 1), date(2025, 3, 31)).isoformat(),
            "list_price": round(random.uniform(19.99, 89.99), 2),
        }
        books.append(book)

    return books


def generate_orders(num_orders: int) -> list[dict]:
    order_statuses = [
        ("new", 10),
        ("completed", 65),
        ("cancelled", 10),
        ("returned", 15),
    ]
    payment_statuses = [
        ("paid", 75),
        ("pending", 15),
        ("failed", 10),
    ]

    orders = []

    for order_id in range(1, num_orders + 1):
        order_status = weighted_choice(order_statuses)

        if order_status == "cancelled":
            payment_status = random.choice(["pending", "failed"])
        else:
            payment_status = weighted_choice(payment_statuses)

        order = {
            "order_id": order_id,
            "customer_id": random.randint(1000, 9999),
            "order_date": random_date(date(2024, 1, 1), date(2025, 3, 31)).isoformat(),
            "order_status": order_status,
            "payment_status": payment_status,
            "total_amount": 0.0,
            "discount_amount": 0.0,
        }
        orders.append(order)

    return orders


def generate_order_items(orders: list[dict], books: list[dict]) -> list[dict]:
    order_items = []
    order_item_id = 1

    for order in orders:
        num_items = random.randint(1, 4)
        chosen_books = random.sample(books, k=min(num_items, len(books)))

        subtotal = 0.0

        for book in chosen_books:
            quantity = random.randint(1, 3)
            unit_price = book["list_price"]
            line_amount = round(quantity * unit_price, 2)
            subtotal += line_amount

            item = {
                "order_item_id": order_item_id,
                "order_id": order["order_id"],
                "book_id": book["book_id"],
                "quantity": quantity,
                "unit_price": unit_price,
                "line_amount": line_amount,
            }
            order_items.append(item)
            order_item_id += 1

        if order["order_status"] == "cancelled":
            discount_amount = 0.0
            total_amount = 0.0
        else:
            discount_amount = round(subtotal * random.choice([0.0, 0.05, 0.1, 0.15]), 2)
            total_amount = round(subtotal - discount_amount, 2)

        order["discount_amount"] = discount_amount
        order["total_amount"] = total_amount

    return order_items


def generate_inventory(books: list[dict], num_warehouses: int = 2) -> list[dict]:
    inventory = []
    inventory_id = 1
    snapshot_date = date(2025, 4, 1).isoformat()

    for book in books:
        for warehouse_id in range(1, num_warehouses + 1):
            stock_on_hand = random.randint(0, 120)
            stock_reserved = random.randint(0, min(20, stock_on_hand))

            row = {
                "inventory_id": inventory_id,
                "book_id": book["book_id"],
                "warehouse_id": warehouse_id,
                "stock_on_hand": stock_on_hand,
                "stock_reserved": stock_reserved,
                "snapshot_date": snapshot_date,
            }
            inventory.append(row)
            inventory_id += 1

    return inventory


def generate_shipments(orders: list[dict]) -> list[dict]:
    carriers = ["DHL", "DPD", "InPost", "UPS", "GLS"]
    shipment_statuses = [
        ("prepared", 20),
        ("in_transit", 30),
        ("delivered", 40),
        ("returned_to_sender", 10),
    ]

    shipments = []
    shipment_id = 1

    for order in orders:
        if order["order_status"] == "cancelled":
            continue

        if random.random() < 0.15:
            continue

        shipment_date_obj = date.fromisoformat(order["order_date"]) + timedelta(days=random.randint(1, 3))
        shipment_status = weighted_choice(shipment_statuses)

        delivery_date = None
        if shipment_status == "delivered":
            delivery_date = shipment_date_obj + timedelta(days=random.randint(1, 5))
        elif shipment_status == "returned_to_sender":
            delivery_date = shipment_date_obj + timedelta(days=random.randint(3, 7))

        shipment = {
            "shipment_id": shipment_id,
            "order_id": order["order_id"],
            "shipment_date": shipment_date_obj.isoformat(),
            "carrier": random.choice(carriers),
            "shipment_status": shipment_status,
            "delivery_date": delivery_date.isoformat() if delivery_date else "",
        }
        shipments.append(shipment)
        shipment_id += 1

    return shipments


def generate_marketing_campaigns(num_campaigns: int) -> list[dict]:
    channels = [
        ("Google Ads", 35),
        ("Facebook Ads", 25),
        ("Instagram Ads", 15),
        ("Email", 15),
        ("Affiliate", 10),
    ]
    objectives = [
        ("awareness", 20),
        ("traffic", 25),
        ("conversion", 40),
        ("retention", 15),
    ]
    target_segments = [
        ("new_customers", 35),
        ("returning_customers", 30),
        ("students", 15),
        ("premium_readers", 10),
        ("parents", 10),
    ]
    statuses = [("planned", 15), ("active", 25), ("finished", 60)]
    prefixes = [
        "Spring", "Summer", "Autumn", "Winter", "Bestseller",
        "Fantasy", "Crime", "Romance", "Business", "Weekend"
    ]

    campaigns = []
    used_names = set()

    for campaign_id in range(1, num_campaigns + 1):
        while True:
            campaign_name = f"{random.choice(prefixes)}_Campaign_{campaign_id}"
            if campaign_name not in used_names:
                used_names.add(campaign_name)
                break

        start_date = random_date(date(2024, 1, 1), date(2025, 2, 20))
        duration_days = random.randint(14, 45)
        end_date = min(start_date + timedelta(days=duration_days), date(2025, 3, 31))

        campaigns.append({
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "channel": weighted_choice(channels),
            "objective": weighted_choice(objectives),
            "target_segment": weighted_choice(target_segments),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "budget": round(random.uniform(1500, 15000), 2),
            "status": weighted_choice(statuses),
            "owner_team": "Marketing",
        })

    return campaigns


def generate_marketing_campaign_products(campaigns: list[dict], books: list[dict]) -> list[dict]:
    promo_types = [
        ("discount", 40),
        ("featured", 25),
        ("homepage_banner", 20),
        ("newsletter", 15),
    ]

    campaign_products = []
    campaign_product_id = 1

    for campaign in campaigns:
        start_date = date.fromisoformat(campaign["start_date"])
        end_date = date.fromisoformat(campaign["end_date"])
        chosen_books = random.sample(books, k=min(random.randint(3, 8), len(books)))
        featured_book_id = random.choice(chosen_books)["book_id"]

        for book in chosen_books:
            promo_type = weighted_choice(promo_types)
            discount_pct = random.choice([0, 5, 10, 15, 20]) if promo_type == "discount" else 0
            promo_price = round(book["list_price"] * (1 - discount_pct / 100), 2)

            campaign_products.append({
                "campaign_product_id": campaign_product_id,
                "campaign_id": campaign["campaign_id"],
                "book_id": book["book_id"],
                "promo_type": promo_type,
                "discount_pct": discount_pct,
                "featured_flag": book["book_id"] == featured_book_id,
                "promo_price": promo_price,
                "valid_from": start_date.isoformat(),
                "valid_to": end_date.isoformat(),
            })
            campaign_product_id += 1

    return campaign_products


def generate_marketing_campaign_daily_metrics(campaigns: list[dict]) -> list[dict]:
    metrics = []

    for campaign in campaigns:
        start_date = date.fromisoformat(campaign["start_date"])
        end_date = date.fromisoformat(campaign["end_date"])
        current_date = start_date

        while current_date <= end_date:
            channel = campaign["channel"]
            objective = campaign["objective"]

            if channel == "Email":
                impressions = random.randint(800, 6000)
                ctr_low, ctr_high = 0.03, 0.12
                cpc_low, cpc_high = 0.05, 0.35
            elif channel in ("Google Ads", "Facebook Ads", "Instagram Ads"):
                impressions = random.randint(2500, 18000)
                ctr_low, ctr_high = 0.01, 0.06
                cpc_low, cpc_high = 0.35, 1.8
            else:
                impressions = random.randint(1000, 9000)
                ctr_low, ctr_high = 0.01, 0.05
                cpc_low, cpc_high = 0.2, 1.0

            clicks = max(1, int(impressions * random.uniform(ctr_low, ctr_high)))
            if objective == "conversion":
                conversion_rate = random.uniform(0.04, 0.18)
            elif objective == "traffic":
                conversion_rate = random.uniform(0.02, 0.08)
            else:
                conversion_rate = random.uniform(0.01, 0.05)

            conversions = min(clicks, int(clicks * conversion_rate))
            sessions = max(clicks, int(clicks * random.uniform(1.0, 1.25)))
            add_to_cart = min(sessions, int(sessions * random.uniform(0.08, 0.3)))
            cost = round(clicks * random.uniform(cpc_low, cpc_high), 2)

            metrics.append({
                "campaign_id": campaign["campaign_id"],
                "event_date": current_date.isoformat(),
                "impressions": impressions,
                "clicks": clicks,
                "cost": cost,
                "sessions": sessions,
                "add_to_cart": add_to_cart,
                "conversions": conversions,
                "source_system": channel.lower().replace(" ", "_").replace("ads", "ads_platform"),
            })
            current_date += timedelta(days=1)

    return metrics


def generate_marketing_published_campaign_sales_attribution(
    campaigns: list[dict],
    campaign_products: list[dict],
    orders: list[dict],
    order_items: list[dict],
    inventory: list[dict],
) -> list[dict]:
    campaign_by_id = {campaign["campaign_id"]: campaign for campaign in campaigns}
    orders_by_id = {order["order_id"]: order for order in orders}

    inventory_by_book = {}
    for row in inventory:
        inventory_by_book.setdefault(row["book_id"], 0)
        inventory_by_book[row["book_id"]] += row["stock_on_hand"] - row["stock_reserved"]

    products_by_campaign = {}
    for row in campaign_products:
        products_by_campaign.setdefault(row["campaign_id"], []).append(row)

    published_rows = []

    for campaign_id, product_rows in products_by_campaign.items():
        campaign = campaign_by_id[campaign_id]
        start_date = date.fromisoformat(campaign["start_date"])
        end_date = date.fromisoformat(campaign["end_date"])
        product_map = {row["book_id"]: row for row in product_rows}

        for item in order_items:
            book_id = item["book_id"]
            if book_id not in product_map:
                continue

            order = orders_by_id[item["order_id"]]
            if order["order_status"] == "cancelled":
                continue

            order_date = date.fromisoformat(order["order_date"])
            if not (start_date <= order_date <= end_date):
                continue

            campaign_product = product_map[book_id]
            stock_available = max(0, inventory_by_book.get(book_id, 0))
            if campaign_product["discount_pct"] > 0:
                attribution_type = "discount_match"
            elif campaign_product["featured_flag"]:
                attribution_type = "featured_product"
            else:
                attribution_type = "in_campaign_window"

            if order["order_status"] == "returned":
                net_sales_amount = round(item["line_amount"] * -1, 2)
                quantity = item["quantity"] * -1
            else:
                net_sales_amount = item["line_amount"]
                quantity = item["quantity"]

            published_rows.append({
                "campaign_id": campaign_id,
                "book_id": book_id,
                "order_id": item["order_id"],
                "order_item_id": item["order_item_id"],
                "order_date": order["order_date"],
                "customer_id": order["customer_id"],
                "quantity": quantity,
                "unit_price": item["unit_price"],
                "line_amount": item["line_amount"],
                "attribution_type": attribution_type,
                "campaign_influence_score": 1.0,
                "net_sales_amount": net_sales_amount,
                "stock_available_at_campaign_snapshot": stock_available,
            })

    return published_rows


def write_csv(filepath: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    validate_directories()

    num_books = 50
    num_orders = 120
    num_campaigns = 12

    books = generate_books(num_books)
    orders = generate_orders(num_orders)
    order_items = generate_order_items(orders, books)
    inventory = generate_inventory(books, num_warehouses=2)
    shipments = generate_shipments(orders)

    marketing_campaigns = generate_marketing_campaigns(num_campaigns)
    marketing_campaign_products = generate_marketing_campaign_products(marketing_campaigns, books)
    marketing_campaign_daily_metrics = generate_marketing_campaign_daily_metrics(marketing_campaigns)
    marketing_published_campaign_sales_attribution = generate_marketing_published_campaign_sales_attribution(
        marketing_campaigns,
        marketing_campaign_products,
        orders,
        order_items,
        inventory,
    )

    write_csv(
        CATALOG_DIR / "books.csv",
        books,
        [
            "book_id", "isbn", "title", "author_name", "publisher_name",
            "category", "format", "publication_date", "list_price"
        ]
    )

    write_csv(
        SALES_DIR / "orders.csv",
        orders,
        [
            "order_id", "customer_id", "order_date", "order_status",
            "payment_status", "total_amount", "discount_amount"
        ]
    )

    write_csv(
        SALES_DIR / "order_items.csv",
        order_items,
        [
            "order_item_id", "order_id", "book_id", "quantity",
            "unit_price", "line_amount"
        ]
    )

    write_csv(
        LOGISTICS_DIR / "inventory.csv",
        inventory,
        [
            "inventory_id", "book_id", "warehouse_id",
            "stock_on_hand", "stock_reserved", "snapshot_date"
        ]
    )

    write_csv(
        LOGISTICS_DIR / "shipments.csv",
        shipments,
        [
            "shipment_id", "order_id", "shipment_date",
            "carrier", "shipment_status", "delivery_date"
        ]
    )

    write_csv(
        MARKETING_DIR / "marketing_campaigns.csv",
        marketing_campaigns,
        [
            "campaign_id", "campaign_name", "channel", "objective",
            "target_segment", "start_date", "end_date", "budget",
            "status", "owner_team"
        ]
    )

    write_csv(
        MARKETING_DIR / "marketing_campaign_products.csv",
        marketing_campaign_products,
        [
            "campaign_product_id", "campaign_id", "book_id", "promo_type",
            "discount_pct", "featured_flag", "promo_price", "valid_from", "valid_to"
        ]
    )

    write_csv(
        MARKETING_DIR / "marketing_campaign_daily_metrics.csv",
        marketing_campaign_daily_metrics,
        [
            "campaign_id", "event_date", "impressions", "clicks", "cost",
            "sessions", "add_to_cart", "conversions", "source_system"
        ]
    )

    write_csv(
        SHARED_DIR / "marketing_published_campaign_sales_attribution.csv",
        marketing_published_campaign_sales_attribution,
        [
            "campaign_id", "book_id", "order_id", "order_item_id", "order_date",
            "customer_id", "quantity", "unit_price", "line_amount",
            "attribution_type", "campaign_influence_score", "net_sales_amount",
            "stock_available_at_campaign_snapshot"
        ]
    )

    print("Wygenerowano pliki:")
    print(f"- {CATALOG_DIR / 'books.csv'}")
    print(f"- {SALES_DIR / 'orders.csv'}")
    print(f"- {SALES_DIR / 'order_items.csv'}")
    print(f"- {LOGISTICS_DIR / 'inventory.csv'}")
    print(f"- {LOGISTICS_DIR / 'shipments.csv'}")
    print(f"- {MARKETING_DIR / 'marketing_campaigns.csv'}")
    print(f"- {MARKETING_DIR / 'marketing_campaign_products.csv'}")
    print(f"- {MARKETING_DIR / 'marketing_campaign_daily_metrics.csv'}")
    print(f"- {SHARED_DIR / 'marketing_published_campaign_sales_attribution.csv'}")


if __name__ == "__main__":
    main()
