select
  order_id,
  customer_id,
  order_date,
  order_status,
  payment_status,
  total_amount,
  discount_amount
from {{ source('raw', 'orders') }}
where order_id is not null
  and total_amount >= 0
