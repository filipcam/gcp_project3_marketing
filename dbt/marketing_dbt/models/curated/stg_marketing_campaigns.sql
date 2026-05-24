with source as (

    select * from {{ source('marketing_raw', 'ext_marketing_campaigns') }}

),

cleaned as (

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
        owner_team,
        load_date,
        source_file,
        current_timestamp() as _dbt_loaded_at
    from source
    where campaign_id is not null

)

select * from cleaned
