with campaigns as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        target_segment,
        start_date,
        end_date,
        budget_amount,
        status,
        owner_team
    from {{ ref('stg_marketing_campaigns') }}

),

daily_metrics as (

    select
        campaign_id,
        event_date,
        impressions,
        clicks,
        cost_amount,
        sessions,
        add_to_cart,
        conversions,
        source_system
    from {{ ref('stg_marketing_campaign_daily_metrics') }}

),

final as (

    select
        dm.campaign_id,
        c.campaign_name,
        c.channel,
        c.objective,
        c.target_segment,
        c.start_date,
        c.end_date,
        c.budget_amount,
        c.status,
        c.owner_team,

        dm.event_date,
        dm.source_system,

        coalesce(dm.impressions, 0) as impressions,
        coalesce(dm.clicks, 0) as clicks,
        coalesce(dm.cost_amount, 0) as cost_amount,
        coalesce(dm.sessions, 0) as sessions,
        coalesce(dm.add_to_cart, 0) as add_to_cart,
        coalesce(dm.conversions, 0) as conversions,

        safe_divide(dm.clicks, dm.impressions) as ctr,
        safe_divide(dm.cost_amount, dm.clicks) as cpc,
        safe_divide(dm.conversions, dm.clicks) as cvr,

        current_timestamp() as _dbt_loaded_at

    from daily_metrics dm
    left join campaigns c
        on dm.campaign_id = c.campaign_id

)

select * from final