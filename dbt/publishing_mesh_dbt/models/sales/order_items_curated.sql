select
  order_item_id,
  order_id,
  book_id,
  quantity,
  unit_price,
  line_amount
from {{ source('raw', 'order_items') }}
where order_item_id is not null
  and order_id is not null
  and book_id is not null
  and quantity > 0
  and unit_price >= 0
  and line_amount >= 0