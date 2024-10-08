SQL_SCRIPT = """SELECT 
                            entity_origin,
                            entity_work,
                            DATE_FORMAT(start, "%Y-%m-%d %H:00:00") as start,
                            end,
                            shift_user_id
                        FROM `collated_cc_rota_shift`
                        WHERE YEAR(start)='2024' AND realm = %s and published = 1"""
