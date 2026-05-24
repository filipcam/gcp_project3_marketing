{{
    config(
        materialized='table',
        description='Published data product. Dzienna wydajność kampanii mediowych. Stable interface.'
    )
}}

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

        coalesce(dm.impressions,  0) as impressions,
        coalesce(dm.clicks,       0) as clicks,
        coalesce(dm.cost_amount,  0) as cost_amount,
        coalesce(dm.sessions,     0) as sessions,
        coalesce(dm.add_to_cart,  0) as add_to_cart,

        safe_divide(dm.clicks,      dm.impressions) as ctr,
        safe_divide(dm.cost_amount, dm.clicks)      as cpc,

        current_timestamp() as _dbt_loaded_at

    from daily_metrics dm
    left join campaigns c using (campaign_id)

)

select * from final
