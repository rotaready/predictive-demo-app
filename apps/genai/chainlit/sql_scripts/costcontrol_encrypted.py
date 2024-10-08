SQL_SCRIPT = """SELECT 
	id, right(ENCRYPT(entity_id),3), type_id, date_of_business, stream_id, sub_stream_id, data_value as revenue
FROM `collated_cc_costcontrol_data`
WHERE YEAR(date_of_business)='2024' and type_id = 2 AND realm = %s
"""
