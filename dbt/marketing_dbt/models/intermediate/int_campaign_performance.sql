with campaigns as (
    select *
    from {{ ref('stg_marketing_campaigns') }}
),

metrics as (
    select *
    from {{ ref('stg_marketing_campaign_daily_metrics') }}
),

agg as (
    select
        campaign_id,
        sum(impressions) as total_impressions,
        sum(clicks) as total_clicks,
        sum(cost_amount) as total_cost_amount,
        sum(sessions) as total_sessions,
        sum(add_to_cart) as total_add_to_cart,
        sum(conversions) as total_conversions
    from metrics
    group by campaign_id
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
    a.total_impressions,
    a.total_clicks,
    a.total_cost_amount,
    a.total_sessions,
    a.total_add_to_cart,
    a.total_conversions,
    safe_divide(a.total_clicks, a.total_impressions) as ctr,
    safe_divide(a.total_cost_amount, a.total_clicks) as cpc,
    safe_divide(a.total_conversions, a.total_clicks) as cvr
from campaigns c
left join agg a using (campaign_id)