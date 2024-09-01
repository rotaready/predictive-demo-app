import os
import numpy as np
import pandas as pd
import mysql.connector
from datetime import datetime


# filter only tier 1,2 realms - keep as tuple for mysql query
realms_shortlist = ('gusto', 
                    'camino', 
                    'maray', 
                    'pizzapilgrims', 
                    'signaturepubs', 
                    'brewdog', 
                    'preto', 
                    'temper', 
                    'bonnieandwild', 
                    'brownsofbrockley', 
                    'itison', 
                    'roseacre', 
                    'spaceandthyme', 
                    'housecafes', 
                    'gh4ox1gb', 
                    'namco', 
                    'hotelfolk', 
                    'warnerleisure', 
                    'nq64')

def get_absence_data():

    rds_host = os.getenv("ML_RDS_HOST")
    rds_user = os.getenv("ML_RDS_USER")
    rds_pwd = os.getenv("ML_RDS_PASSWORD")

    rds_db = 'rr_core'  
    
    # NB query is about 6 secs for 2024 only, tier 1 and 2 clients or
    # 40 secs for tier 1 and 2 clients, or 3 mins for all realms

    query = f"""select 
                    *,
            -- no. of hours prior to start date the request was submitted
            TIME_TO_SEC(timediff(CONVERT(submit_date, DATETIME),CONVERT(date_start, DATETIME)))/(24*60*60) as request_lt_days 
            from collated_absence_header
            where year(date_start) >= 2024 and cancelled = 0 and approved = 1 and realm in {realms_shortlist}"""

    conn = mysql.connector.connect(
            host=rds_host, user=rds_user, password=rds_pwd, database=rds_db
            )

    absences = pd.read_sql_query(query, con=conn) # NB this gets closed after returning to main()

    conn.close()

    absences.to_csv('apps/analytics/recommendations/absences.csv')

    return absences


def get_num_outliers (column, ptile):

    #q1 = np.percentile(column, 25)
    q3 = np.percentile(column, ptile)

    return sum(column>q3) # use sum((column<q1) | (column>q3)) for ALL outliers


def absences_analyis(**kwargs):

    metrics_list = ['most_absences',
                    'least_absences', 
                    'longest_absences',
                    'shortest_time_on_absence',
                    'longest_avg_absence_duration',
                    'shortest_avg_absence_duration',
                    'earliest_absence_leadtime',
                    'latest_absence_leadtime',
                    'most_num_late_absences',
                    'least_num_late_absences',
                    'most_num_last_min_absences', 
                    'least_num_last_min_absences',
                    'highest_proportion_last_min_absences',
                    'lowest_proportion_last_min_absences']

    # get data
    try: # open the file is its there
        absences = pd.read_csv('apps/analytics/recommendations/absences.csv')
    except: # read direct from RDS
        absences = get_absence_data()

    # add time info
    # 1) convert dates to pandas datetime format
    absences['date_start'] = pd.to_datetime(absences['date_start'], format='%Y-%m-%d')
    # 2) add year, month, day columns
    absences['start_year'] = absences['date_start'].dt.year
    absences['start_month'] = absences['date_start'].dt.month
    absences['start_day'] = absences['date_start'].dt.day

    # filter this months absences (based on absence start date)
    monthly_absences = absences[(absences.start_year==datetime.now().year) & 
                                (absences.start_month==datetime.now().month)]
    
    # summary for this month 

    monthly_absence_summary = monthly_absences.groupby(by = ['realm'], as_index = False).apply(lambda x: pd.Series({'num_absences': x['id'].count(),
                                                                                                'total_absence_duration': x['total_days'].sum(),
                                                                                                'avg_absence_duration': x['total_hours'].mean(),
                                                                                                'avg_request_leadtime': x['request_lt_days'].mean(),
                                                                                                'num_outliers_75': get_num_outliers(x['request_lt_days'], 75),
                                                                                                'num_outliers_95': get_num_outliers(x['request_lt_days'], 95),
                                                                                                'outlier_proportion': get_num_outliers(x['request_lt_days'], 95) / x['id'].count()}))
    
    
    # *check* refactor below using a list of metrics                                                                                              
    monthly_absence_summary = monthly_absence_summary.astype({"num_absences":"int",
                                                            "total_absence_duration":"int",
                                                                "avg_absence_duration":"int",
                                                                    "avg_request_leadtime":"int",
                                                                        "num_outliers_75":"int",
                                                                            "num_outliers_95":"int"})                                                                                            

    most_absences = monthly_absence_summary[monthly_absence_summary.num_absences == max(monthly_absence_summary.num_absences)][['realm','num_absences']]
    least_absences = monthly_absence_summary[monthly_absence_summary.num_absences == min(monthly_absence_summary.num_absences)][['realm','num_absences']]
    longest_absences = monthly_absence_summary[monthly_absence_summary.total_absence_duration == max(monthly_absence_summary.total_absence_duration)][['realm','total_absence_duration']]
    shortest_time_on_absence = monthly_absence_summary[monthly_absence_summary.total_absence_duration == min(monthly_absence_summary.total_absence_duration)][['realm','total_absence_duration']]
    longest_avg_absence_duration = monthly_absence_summary[monthly_absence_summary.avg_absence_duration == max(monthly_absence_summary.avg_absence_duration)][['realm','avg_absence_duration']]
    shortest_avg_absence_duration = monthly_absence_summary[monthly_absence_summary.avg_absence_duration == min(monthly_absence_summary.avg_absence_duration)][['realm','avg_absence_duration']]
    earliest_avg_absence_leadtime = monthly_absence_summary[monthly_absence_summary.avg_request_leadtime == min(monthly_absence_summary.avg_request_leadtime)][['realm','avg_request_leadtime']]
    latest_avg_absence_leadtime = monthly_absence_summary[monthly_absence_summary.avg_request_leadtime == max(monthly_absence_summary.avg_request_leadtime)][['realm','avg_request_leadtime']]
    most_num_late_absences = monthly_absence_summary[monthly_absence_summary.num_outliers_75 == max(monthly_absence_summary.num_outliers_75)][['realm','num_outliers_75']]
    least_num_late_absences = monthly_absence_summary[monthly_absence_summary.num_outliers_75 == min(monthly_absence_summary.num_outliers_75)][['realm','num_outliers_75']]
    most_num_last_min_absences = monthly_absence_summary[monthly_absence_summary.num_outliers_95 == max(monthly_absence_summary.num_outliers_95)][['realm','num_outliers_95']]
    least_num_last_min_absences = monthly_absence_summary[monthly_absence_summary.num_outliers_95 == min(monthly_absence_summary.num_outliers_95)][['realm','num_outliers_95']]
    highest_proportion_last_min_absences = monthly_absence_summary[monthly_absence_summary.outlier_proportion == max(monthly_absence_summary.outlier_proportion)][['realm','outlier_proportion']]
    lowest_proportion_last_min_absences = monthly_absence_summary[monthly_absence_summary.outlier_proportion == min(monthly_absence_summary.outlier_proportion)][['realm','outlier_proportion']]
    
    vals = [most_absences.to_string(header=False,index=False),
            least_absences.to_string(header=False,index=False),
            longest_absences.to_string(header=False,index=False),
            shortest_time_on_absence.to_string(header=False,index=False),
            longest_avg_absence_duration .to_string(header=False,index=False),
            shortest_avg_absence_duration .to_string(header=False,index=False),
            earliest_avg_absence_leadtime.to_string(header=False,index=False),
            latest_avg_absence_leadtime.to_string(header=False,index=False),
            most_num_late_absences .to_string(header=False,index=False),
            least_num_late_absences .to_string(header=False,index=False),
            most_num_last_min_absences .to_string(header=False,index=False),
            least_num_last_min_absences .to_string(header=False,index=False),
            highest_proportion_last_min_absences .to_string(header=False,index=False),
            lowest_proportion_last_min_absences .to_string(header=False,index=False)
    ]

    recommendations  = dict(zip(metrics_list, vals))


    return recommendations
