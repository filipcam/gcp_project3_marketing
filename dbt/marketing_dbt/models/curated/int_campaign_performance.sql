-- Łączy kampanie marketingowe z metrykami mediowymi i rzeczywistą sprzedażą.
-- Źródło sprzedaży: book_daily_sales (zastąpienie top_products MVP).
-- Agregacja sprzedaży ograniczona do okresu trwania kampanii (start_date – end_date).

with campaigns as (

    select *
    from {{ ref('stg_marketing_campaigns') }}

),

metrics as (

    select *
    from {{ ref('stg_marketing_campaign_daily_metrics') }}

),

campaign_products as (

    select *
    from {{ ref('stg_marketing_campaign_products') }}

),

-- Nowe źródło sprzedaży: dzienne dane zamiast zagregowanego MVP
daily_sales as (

    select *
    from {{ ref('stg_book_daily_sales') }}

),

-- Agregacja metryk mediowych per kampania
agg_metrics as (

    select
        campaign_id,
        sum(impressions)  as total_impressions,
        sum(clicks)       as total_clicks,
        sum(cost_amount)  as total_cost_amount,
        sum(sessions)     as total_sessions,
        sum(add_to_cart)  as total_add_to_cart
    from metrics
    group by campaign_id

),

-- Agregacja sprzedaży per book_id w oknie czasowym kampanii
-- JOIN przez campaign_products → tylko książki przypisane do kampanii
agg_sales as (

    select
        cp.campaign_id,
        sum(ds.orders_count)       as total_orders,
        sum(ds.items_sold)         as total_items_sold,
        sum(ds.gross_sales_amount) as total_revenue
    from campaign_products cp
    inner join daily_sales ds
        using (book_id)
    inner join campaigns c
        using (campaign_id)
    where ds.sales_date between c.start_date and c.end_date
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
    coalesce(a.total_impressions,  0) as total_impressions,
    coalesce(a.total_clicks,       0) as total_clicks,
    coalesce(a.total_cost_amount,  0) as total_cost_amount,
    coalesce(a.total_sessions,     0) as total_sessions,
    coalesce(a.total_add_to_cart,  0) as total_add_to_cart,

    -- Metryki sprzedażowe (okno kampanii)
    coalesce(s.total_orders,      0) as total_orders,
    coalesce(s.total_items_sold,  0) as total_items_sold,
    coalesce(s.total_revenue,     0) as total_revenue,

    -- Wskaźniki wyliczane
    safe_divide(a.total_clicks,       a.total_impressions)  as ctr,
    safe_divide(a.total_cost_amount,  a.total_clicks)       as cpc,
    safe_divide(s.total_items_sold,   a.total_clicks)       as cvr,
    safe_divide(a.total_cost_amount,  s.total_items_sold)   as cost_per_sale

from campaigns c
left join agg_metrics a using (campaign_id)
left join agg_sales   s using (campaign_id)
