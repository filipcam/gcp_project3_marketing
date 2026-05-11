select
  oi.book_id,
  count(distinct oi.order_id) as total_orders,
  sum(oi.quantity) as total_items_sold,
  sum(oi.line_amount) as gross_sales_amount
from {{ ref('order_items_curated') }} oi
join {{ ref('orders_curated') }} o
  on oi.order_id = o.order_id
group by oi.book_id