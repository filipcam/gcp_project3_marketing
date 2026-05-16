with source as (

    select * from {{ source('marketing_raw', 'marketing_campaign_daily_metrics') }}

),

cleaned as (

    select
        campaign_id,
        event_date,
        impressions,
        clicks,
        cost_amount,
        sessions,
        add_to_cart,
        conversions,
        source_system,
        load_date,
        generated_at,
        source_file,
        current_timestamp() as _dbt_loaded_at
    from source
    where campaign_id is not null
      and event_date is not null

)

select * from cleaned