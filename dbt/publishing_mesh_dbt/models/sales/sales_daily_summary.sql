select
  o.order_date as sales_date,
  count(distinct o.order_id) as orders_count,
  sum(oi.quantity) as items_sold,
  sum(oi.line_amount) as gross_sales_amount
from {{ ref('orders_curated') }} o
join {{ ref('order_items_curated') }} oi
  on o.order_id = oi.order_id
group by o.order_date