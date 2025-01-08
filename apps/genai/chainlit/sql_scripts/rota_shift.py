SQL_SCRIPT = """SELECT 
                            entity_origin,
                            entity_work,
                            DATE_FORMAT(start, "%Y-%m-%d %H:00:00") as start,
                            end,
                            shift_user_id
                        FROM `cc_rota_shift`
                        WHERE YEAR(start)='2024' AND published = 1"""
# use collated_ DB and add realm = %s in WHERE if using rr_core
