with campaigns as (
    select *
    from {{ ref('stg_marketing_campaigns') }}
),

metrics as (
    select *
    from {{ ref('stg_marketing_campaign_daily_metrics') }}
),

-- Dane sprzedażowe z domeny Sales
-- TODO: po uzyskaniu dostępu do orders_curated zastąpić join poniżej:
-- left join sales s on cp.book_id = s.book_id
--     and s.order_date between c.start_date and c.end_date
-- Wymaga kolumny order_date w źródle Sales.
sales as (
    select book_id, total_orders, total_items_sold
    from {{ source('sales', 'top_products') }}
),

-- Mapowanie kampania → book_id
campaign_products as (
    select *
    from {{ ref('stg_marketing_campaign_products') }}
),

-- Agregacja metryk mediowych per kampania
agg_metrics as (
    select
        campaign_id,
        sum(impressions)   as total_impressions,
        sum(clicks)        as total_clicks,
        sum(cost_amount)   as total_cost_amount,
        sum(sessions)      as total_sessions,
        sum(add_to_cart)   as total_add_to_cart
    from metrics
    group by campaign_id
),

-- Agregacja sprzedaży per kampania (przez book_id)
agg_sales as (
    select
        cp.campaign_id,
        sum(s.total_orders)      as total_orders,
        sum(s.total_items_sold)  as total_items_sold
    from campaign_products cp
    left join sales s using (book_id)
    group by cp.campaign_id
)

select
    c.campaign_id,
    c.campaign_name,
    c.channel,
    c.objective,
    c.target_segment,
    c.start_date,
    c.end_date,
    c.budget_amount,
    c.status,
    c.owner_team,
    -- Metryki mediowe
    a.total_impressions,
    a.total_clicks,
    a.total_cost_amount,
    a.total_sessions,
    a.total_add_to_cart,
    -- Metryki sprzedażowe z domeny Sales
    s.total_orders,
    s.total_items_sold,
    -- Wskaźniki wyliczane
    safe_divide(a.total_clicks, a.total_impressions)      as ctr,
    safe_divide(a.total_cost_amount, a.total_clicks)      as cpc,
    safe_divide(s.total_items_sold, a.total_clicks)       as cvr,
    safe_divide(a.total_cost_amount, s.total_items_sold)  as cost_per_sale
from campaigns c
left join agg_metrics a using (campaign_id)
left join agg_sales s   using (campaign_id)