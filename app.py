from flask import Flask, request, send_file, jsonify
from io import BytesIO
import os
import zipfile
import pandas as pd
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

zip_path= "C:\Users\rauna\Documents\GitHub\vehicle-trail-report-api\NU-raw-location-dump.zip"
extract_path= "C:\Users\rauna\Documents\GitHub\vehicle-trail-report-api\extracted"

def unzip_data(zip_path, extract_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

def read_trip_info(file_path):
    return pd.read_csv(file_path)

def read_vehicle_trails(folder_path):
    trails = {}
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            file_path = os.path.join(folder_path, file_name)
            df = pd.read_csv(file_path)
            trails[file_name] = df
    return trails

def filter_trails(trails, start_time, end_time):
    filtered_trails = {}
    for vehicle, df in trails.items():
        df['tis'] = pd.to_datetime(df['tis'], unit='s')
        mask = (df['tis'] >= start_time) & (df['tis'] <= end_time)
        filtered_df = df.loc[mask]
        if not filtered_df.empty:
            filtered_trails[vehicle] = filtered_df
    return filtered_trails

def filter_trip_info(trip_info, start_time, end_time):
    trip_info['date_time'] = pd.to_datetime(trip_info['date_time'], format='%Y%m%d%H%M%S')
    mask = (trip_info['date_time'] >= start_time) & (trip_info['date_time'] <= end_time)
    return trip_info.loc[mask]

def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0  # Radius of the Earth in km
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance

def compute_metrics(trails, trip_info):
    report_data = []
    for vehicle, df in trails.items():
        distance = 0.0
        for i in range(1, len(df)):
            distance += haversine(df.iloc[i-1]['lon'], df.iloc[i-1]['lat'], df.iloc[i]['lon'], df.iloc[i]['lat'])

        avg_speed = df['spd'].mean()
        num_trips = trip_info[trip_info['vehicle_number'] == df.iloc[0]['lic_plate_no']].shape[0]
        num_speed_violations = df['osf'].sum()
        transporter_name = trip_info[trip_info['vehicle_number'] == df.iloc[0]['lic_plate_no']]['transporter_name'].iloc[0]

        report_data.append({
            'License plate number': df.iloc[0]['lic_plate_no'],
            'Distance': distance,
            'Number of Trips Completed': num_trips,
            'Average Speed': avg_speed,
            'Transporter Name': transporter_name,
            'Number of Speed Violations': num_speed_violations
        })
    return report_data

def generate_excel_report(report_data, output_path):
    df = pd.DataFrame(report_data)
    df.to_excel(output_path, index=False)

@app.route('/generate-report', methods=['GET'])
def generate_report():
    try:
        start_time = int(request.args.get('start_time'))
        end_time = int(request.args.get('end_time'))

        start_time = datetime.utcfromtimestamp(start_time)
        end_time = datetime.utcfromtimestamp(end_time)

        trip_info = read_trip_info('C:\Users\rauna\Documents\GitHub\vehicle-trail-report-api\Trip-Info.csv')
        trails = read_vehicle_trails('C:\Users\rauna\Documents\GitHub\vehicle-trail-report-api\extracted')

        filtered_trails = filter_trails(trails, start_time, end_time)
        filtered_trip_info = filter_trip_info(trip_info, start_time, end_time)

        if not filtered_trails or filtered_trip_info.empty:
            return jsonify({'error': 'No data available for the specified time range'}), 404

        report_data = compute_metrics(filtered_trails, filtered_trip_info)

        output = BytesIO()
        generate_excel_report(report_data, output)
        output.seek(0)

        return send_file(output, attachment_filename='Asset_Report.xlsx', as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
