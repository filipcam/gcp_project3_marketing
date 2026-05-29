-- int_campaign_book_attribution.sql
-- Granularność: campaign_id × book_id
-- Sprzedaż każdej książki w oknie czasowym kampanii

-- int_campaign_book_attribution.sql
-- Granularność: campaign_id × book_id
-- Wszystkie książki z kampanii; sprzedaż NULL jeśli brak transakcji w oknie

with campaign_products as (
    select campaign_id, book_id, promo_type, featured_flag
    from {{ ref('stg_marketing_campaign_products') }}
),

campaigns as (
    select campaign_id, start_date, end_date
    from {{ ref('stg_marketing_campaigns') }}
),

daily_sales as (
    select * from {{ ref('stg_book_daily_sales') }}
)

select
    cp.campaign_id,
    cp.book_id,
    cp.promo_type,
    cp.featured_flag,
    sum(ds.orders_count)       as total_orders,
    sum(ds.items_sold)         as total_items_sold,
    sum(ds.gross_sales_amount) as total_revenue
from campaign_products cp
inner join campaigns c using (campaign_id)
left join daily_sales ds
    on  ds.book_id    = cp.book_id
    and ds.sales_date between c.start_date and c.end_date
group by
    cp.campaign_id,
    cp.book_id,
    cp.promo_type,
    cp.featured_flag