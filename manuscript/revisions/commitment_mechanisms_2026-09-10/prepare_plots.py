import numpy as np
import pandas as pd
import refine_offers as f

S=f.SOURCE
p=pd.read_csv(S/'pi_diagnostic_resolved.csv')
p=p[(p.miss_rate==0)&(p.fraction==1)&p.variant.str.startswith('u')].copy()
p['category']=np.where(p.classification=='instantaneous_supply_infeasible','Immediate shortage',np.where(p.classification=='model_infeasible','Other infeasible',np.where(p.causal_success,'Both feasible','PI feasible; causal failure')))
p.groupby(['variant','category']).size().reset_index(name='cases').to_csv(S/'ready_pi_categories.csv',index=False)
c=pd.read_csv(S/'refinement_cost_components.csv').query('offerable_zero')
long=[]
for row in c.itertuples():
    for field,label in [('waiting_annual_usd','Waiting'),('energy_annual_usd','Electricity'),('delivery_credit_annual_usd','Delivery credit')]:long.append(dict(program=row.program,component=label,value_per_kw=getattr(row,field)/row.accounting_offered_kw,total_per_kw=row.net_operating_per_kw_q95))
pd.DataFrame(long).to_csv(S/'ready_operating_components.csv',index=False)
front=pd.read_csv(S/'refinement_price_frontier.csv');net=[]
for row in front.query('endpoint=="zero" and missed_work_price==0').itertuples():
    for price in np.unique(np.r_[np.arange(0.,751.,5.),250.,max(0.,-row.intercept/(row.slope-1))]):
        net.append(dict(waiting_price=row.waiting_price,fee=row.site_fee_annual_usd,price=price,net4=price*row.accounting_offer_4h-row.operating_4h_annual-row.site_fee_annual_usd,net8=price*row.accounting_offer_8h-row.operating_8h_annual-row.site_fee_annual_usd,difference=price*(row.accounting_offer_8h-row.accounting_offer_4h)-row.operating_8h_annual+row.operating_4h_annual))
pd.DataFrame(net).to_csv(S/'ready_annual_values.csv',index=False)
maps=[('3','a','refinement_selected_confirmed.csv','all','selected_capacity_kw;confirmation_successes;confirmation_lower'),('3','b','ready_pi_categories.csv','all 15 zero-loss full-request diagnoses','variant;category;cases'),('3','c','external_cross_score_weekly.csv','fraction=.75; .5 supplies cross-score control','week;successes_1pct;successes_zero;instantaneous_shortage'),('3','d','weighted_week_summary.csv','chronological;fraction=.5','week;weight;successes_zero'),
('6','a','physical_operating_exposure.csv','offerable_zero;delay_exposure_gpu_h_h','model_series_mean;model_series_p05;model_series_p95'),('6','b','ready_operating_components.csv','all','program;component;value_per_kw;total_per_kw'),('6','c','refinement_economic_sensitivity.csv','offerable_zero;missed_work_price=0;site_fee_annual_usd=0','waiting_price;payment_per_kw'),('6','d','ready_refinement_price_curves.csv','price_4h<=750','waiting_price;price_4h;required_price_8h'),
('S3','a,b','refinement_development_summary.csv','success_1pct or success_zero','capacity_kw;wilson_lower'),('S3','c','../operating_tradeoffs/confirmation_summary.csv','full repeated H8P16 g10 success_1pct','instantaneous_supply_limited_trials;failed_deadline_miss;trials'),('S3','d','../operating_tradeoffs/target_call_pairs.csv','H8P16;g10','fresh_target_electrical_successes;repeated_target_electrical_successes'),
('S5','a','ready_annual_values.csv','fee=0','price;difference;waiting_price'),('S5','b','refinement_economic_sensitivity.csv','offerable_zero;waiting_price=.005;fee=0','missed_work_price;payment_per_kw'),('S5','c','ready_annual_values.csv','price=250;waiting_price=.005;fee in 0,2500,25000','fee;net4;net8'),('S5','d','refinement_price_frontier.csv','zero;waiting_price=.005;loss=0;fee in 0,2500,25000','slope;intercept;nonparticipation_floor;four_hour_entry')]
pd.DataFrame(maps,columns=['figure','panel','table','filter','ready_value_columns']).to_csv(S/'PANEL_DATA_MAP.csv',index=False)
