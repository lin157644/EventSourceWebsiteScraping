from pymongo import MongoClient

MONGO_USER = 'admin'
MONGO_PASSWORD = 'widmwidm9527'
MONGO_HOST_ETL = "140.115.54.44"
MONGO_PORT_ETL = 27000
DATABASE_ETL = 'ETL-api-creator'

EXTRACTOR_COLLECTION = 'extractors'
TEMP_EXTRACTED_DATA_COLLECTION = 'temp-extracted-data'


def get_database_etl():
    client = MongoClient(f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST_ETL}:{MONGO_PORT_ETL}")
    return client[DATABASE_ETL]


# extractor's serial number
serial_number = '3cvrjw1nbkuo7p5yx'

etl_extractors_collection = get_database_etl().get_collection(EXTRACTOR_COLLECTION)
extractor_result = etl_extractors_collection.find_one({'serialNumber': serial_number})

temp_extracted_data_collection = get_database_etl().get_collection(TEMP_EXTRACTED_DATA_COLLECTION)
temp_result = temp_extracted_data_collection.find_one({'serialNumber': serial_number})

print(f"mainSetIndex: {extractor_result['mainSetIndex']},\
        lastExtractedDateTime: {extractor_result['lastExtractedDateTime']}")

# return list data of main set
main_set_data = temp_result['setsData'][extractor_result['mainSetIndex']]
print(main_set_data)
