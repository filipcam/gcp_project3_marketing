import csv
import random
import argparse
from datetime import datetime
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
SALES_DIR = BASE_DIR / "sales"
CATALOG_DIR = BASE_DIR / "catalog"


def weighted_choice(options):
    values = [item[0] for item in options]
    weights = [item[1] for item in options]
    return random.choices(values, weights=weights, k=1)[0]


def load_books(filepath: Path) -> list[dict]:
    books = []
    with open(filepath, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row["book_id"] = int(row["book_id"])
            row["list_price"] = float(row["list_price"])
            books.append(row)
    return books


def infer_num_orders_from_weekday(load_date: str) -> int:
    """
    Returns a realistic daily order volume based on day of week.
    Monday = 0, Sunday = 6
    """
    dt = datetime.strptime(load_date, "%Y-%m-%d").date()
    weekday = dt.weekday()

    # Monday-Friday
    if weekday in (0, 1, 2, 3, 4):
        return random.randint(25, 60)

    # Saturday
    if weekday == 5:
        return random.randint(12, 30)

    # Sunday
    return random.randint(8, 22)


def build_order_id(load_date: str, sequence_number: int) -> int:
    """
    Builds a globally unique order_id using load_date and a daily sequence.
    Example:
    load_date = 2026-04-30
    sequence_number = 1
    order_id = 202604300001
    """
    date_part = load_date.replace("-", "")
    return int(f"{date_part}{sequence_number:04d}")


def build_order_item_id(load_date: str, sequence_number: int) -> int:
    """
    Builds a globally unique order_item_id using load_date and a daily sequence.
    Example:
    load_date = 2026-04-30
    sequence_number = 1
    order_item_id = 202604300001
    """
    date_part = load_date.replace("-", "")
    return int(f"{date_part}{sequence_number:04d}")


def generate_orders(num_orders: int, load_date: str) -> list[dict]:
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

    for i in range(1, num_orders + 1):
        order_id = build_order_id(load_date, i)
        order_status = weighted_choice(order_statuses)

        if order_status == "cancelled":
            payment_status = random.choice(["pending", "failed"])
        else:
            payment_status = weighted_choice(payment_statuses)

        orders.append(
            {
                "order_id": order_id,
                "customer_id": random.randint(1000, 9999),
                "order_date": load_date,
                "order_status": order_status,
                "payment_status": payment_status,
                "total_amount": 0.0,
                "discount_amount": 0.0,
                "load_date": load_date,
            }
        )

    return orders


def generate_order_items(orders: list[dict], books: list[dict], load_date: str) -> list[dict]:
    order_items = []
    order_item_sequence = 1

    for order in orders:
        num_items = random.randint(1, 4)
        chosen_books = random.sample(books, k=min(num_items, len(books)))
        subtotal = 0.0

        for book in chosen_books:
            quantity = random.randint(1, 3)
            unit_price = float(book["list_price"])
            line_amount = round(quantity * unit_price, 2)
            subtotal += line_amount

            order_item_id = build_order_item_id(load_date, order_item_sequence)

            order_items.append(
                {
                    "order_item_id": order_item_id,
                    "order_id": order["order_id"],
                    "book_id": int(book["book_id"]),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_amount": line_amount,
                    "load_date": load_date,
                }
            )
            order_item_sequence += 1

        if order["order_status"] == "cancelled":
            discount_amount = 0.0
            total_amount = 0.0
        else:
            discount_amount = round(subtotal * random.choice([0.0, 0.05, 0.1, 0.15]), 2)
            total_amount = round(subtotal - discount_amount, 2)

        order["discount_amount"] = discount_amount
        order["total_amount"] = total_amount

    return order_items


def write_csv(filepath: Path, rows: list[dict], fieldnames: list[str]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-date", required=True, help="Load date in YYYY-MM-DD format")
    parser.add_argument(
        "--num-orders",
        type=int,
        default=None,
        help="Optional manual override for number of daily orders",
    )
    args = parser.parse_args()

    # Validate date format
    datetime.strptime(args.load_date, "%Y-%m-%d")

    books_path = CATALOG_DIR / "books.csv"
    books = load_books(books_path)

    num_orders = args.num_orders if args.num_orders is not None else infer_num_orders_from_weekday(args.load_date)

    orders = generate_orders(num_orders, args.load_date)
    order_items = generate_order_items(orders, books, args.load_date)

    orders_path = SALES_DIR / "orders" / f"load_date={args.load_date}" / "orders.csv"
    order_items_path = SALES_DIR / "order_items" / f"load_date={args.load_date}" / "order_items.csv"

    write_csv(
        orders_path,
        orders,
        [
            "order_id",
            "customer_id",
            "order_date",
            "order_status",
            "payment_status",
            "total_amount",
            "discount_amount",
            "load_date",
        ],
    )

    write_csv(
        order_items_path,
        order_items,
        [
            "order_item_id",
            "order_id",
            "book_id",
            "quantity",
            "unit_price",
            "line_amount",
            "load_date",
        ],
    )

    print("Generated:")
    print(f"- {orders_path}")
    print(f"- {order_items_path}")
    print(f"- num_orders={num_orders}")
    print(f"- num_order_items={len(order_items)}")


if __name__ == "__main__":
    main()