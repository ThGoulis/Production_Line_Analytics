import pandas as pd
import argparse
import sys

def main():
    
    parser = argparse.ArgumentParser(
                        prog='KPIs Reports',
                        description='Provide KPIs for product lines process')
    
    parser.add_argument('--kpis', help='this use argument: "gr-np-47"')
    parser.add_argument('--runtimes', help='this use argument: total')

    args = parser.parse_args()

    working_data = load_validate_transform_data()

    if args.kpis:

        print("Process start for product line gr-np-47\n")

        result = product_line_gr_np_47(working_data)

        print("Report for product line gr-np-47:\n\n",result,"\n")

        result.to_csv("gr-np-47.csv", index=False)

        print("Process Completed.\nCheck the output file gr-np-47.csv for information")

    elif args.runtimes:

        print("Process start for uptime and downtime of the whole production and \ncalcultate the production line ID with the worst downtime")
        
        result = total_runtime(working_data)

        result.to_csv("kpi_results.csv", index=False)

        print(f"\nProcess Completed with the following result:\n\n {result.T.to_string(header=False)}\n\nThe result saved to: kpi_results.csv")

    else:
        parser.print_help() 
    

def load_validate_transform_data():

    # load dataset
    df = pd.read_csv("dataset.csv", dtype="string")

    # keep only headers from file
    input_header = df.columns.tolist()

    # expected headers from file 
    expected_headers = [
        "production_line_id",
        "status",
        "timestamp"
    ]

    # validate headers before the process starts
    if not (input_header == expected_headers):
        exit("Wrong headers in csv file.\nProcess terminate")

    # expected status
    expected_values = {"START", "ON", "STOP"}

    # find if there is invalid values in collumn status and store it
    invalid_values = df.loc[~df["status"].isin(expected_values), "status"].unique()

    # validate the result from invalid values and exit the program if appears
    if invalid_values:
        exit(
            f"Wrong values in status. Allowed: {expected_values}. \n"
            f"Invalid: {invalid_values}. Process terminate"
        )

    working_data = df

    # convert column timestamp to datetime
    working_data["timestamp"] = pd.to_datetime(working_data["timestamp"], format="%Y-%m-%dT%H:%M:%S", errors="coerce")

    # make normalize on collumn status for better perfomance and avoid wrong data 
    mapping = {"START": 0, "ON": 1, "STOP": 2}

    # apply mapping to collumn
    working_data["status"] = working_data["status"].map(mapping)

    return working_data

def product_line_gr_np_47(working_data):

    # filtered data 
    filtered_data_gr_np_47 = working_data[working_data["production_line_id"] == "gr-np-47"]

    # sort data
    sort_data_gr_np_47 = filtered_data_gr_np_47.sort_values(by=["production_line_id", "timestamp"], ascending=True)

    # create collumn season_tracking as sequence counter of runs per production line ID
    sort_data_gr_np_47["season_tracking"] = sort_data_gr_np_47.groupby("production_line_id")["status"].transform(lambda x: (x == 0).cumsum())

    # Keep only the start and the end of every production process
    gr_np_47_mask = sort_data_gr_np_47[sort_data_gr_np_47["status"].isin([0, 2])].copy()

    # filtered data 
    gr_np_47_mask["start_timestamp"] = gr_np_47_mask["timestamp"].where(gr_np_47_mask["status"] == 0)
    gr_np_47_mask["stop_timestamp"]  = gr_np_47_mask["timestamp"].where(gr_np_47_mask["status"] == 2) 

    # Group data per id and season tracking and calculate first and last timestamp | as_index=False -> in purpose to fill all the lines
    tracing_gr_np_47 = (
        gr_np_47_mask.groupby(["production_line_id", "season_tracking"], as_index=False)
        .agg(
            start_timestamp=("start_timestamp", "min"),
            stop_timestamp=("stop_timestamp", "max"),
        )
    )

    # calculate the duration of every production process
    tracing_gr_np_47["duration"] = tracing_gr_np_47["stop_timestamp"] - tracing_gr_np_47["start_timestamp"]
    return_result = tracing_gr_np_47[["start_timestamp", "stop_timestamp", "duration"]]

    return return_result

def total_runtime(working_data):

    # sort data from dataset
    sort_data = working_data.sort_values(by=["production_line_id", "timestamp"], ascending=True)

    # get max and min from timestamp from whole dataset
    dataset_start = sort_data["timestamp"].min()
    dataset_end   = sort_data["timestamp"].max()

    # calculate the total production line time
    total_production_runtime = dataset_end - dataset_start

    # select the first value of every line base on production line ID and status and store to seperate df
    first_status = sort_data.groupby("production_line_id")["status"].first()

    # find if the first status of production line ID is already START
    need_backfill = first_status[first_status == 1].index

    # store those values into a new dataset in purpose to insert them to main dataframe
    synthetic_rows = pd.DataFrame({
        "production_line_id": need_backfill,
        "status": 0,
        "timestamp": dataset_start
    })
    
    # merge data from both dataframes and order them again via production line ID and timestamp
    sort_data = pd.concat([sort_data, synthetic_rows], ignore_index=True).sort_values(["production_line_id", "timestamp"])

    # create collumn season_tracking as sequence counter of runs per production line ID
    sort_data["season_tracking"] = (sort_data["status"].eq(0).groupby(sort_data["production_line_id"]).cumsum())

    # # filtered data 
    mask = sort_data[sort_data["status"].isin([0, 2])]

    # trace for every run the START and the STOP process 
    mask["start_timestamp"] = mask["timestamp"].where(mask["status"] == 0)
    mask["stop_timestamp"]  = mask["timestamp"].where(mask["status"] == 2) 

    # Group data per id and season tracking and calculate first and last timestamp | as_index=False -> in purpose to fill all the lines
    tracing = (
        mask.groupby(["production_line_id", "season_tracking"], as_index=False)
        .agg(
            start_timestamp=("start_timestamp", "min"),
            stop_timestamp=("stop_timestamp", "max"),
        )
    )

    # check if runs was START without STOP
    tracing["is_open"] = tracing["stop_timestamp"].isna() & tracing["start_timestamp"].notna()

    # close opens runs and set as STOP the latest dataset timestamp
    tracing.loc[tracing["is_open"], "stop_timestamp"] = dataset_end

    # calculate the difference between start and stop timestamp and stored to new collumn 
    tracing["duration"] = tracing["stop_timestamp"] - tracing["start_timestamp"]

    # calculate the uptime per production line
    uptime_per_prd = tracing.groupby("production_line_id")["duration"].sum()

    # calcultate the total uptime
    total_uptime = uptime_per_prd.sum()
    
    # calculate the downtime per product line id
    downtime_per_prd = total_production_runtime - uptime_per_prd

    # calculate the total downtime
    total_downtime = downtime_per_prd.sum()

    # find the worst production line ID 
    worst_line_id = downtime_per_prd.idxmax()
    worst_line_downtime = downtime_per_prd.loc[worst_line_id]

    # store Series to Dataframe in purpose to export into csv
    results = pd.DataFrame([{
        "total_uptime": total_uptime,
        "total_downtime": total_downtime,
        "worst_line_id": worst_line_id,
        "worst_line_downtime": worst_line_downtime
    }])
    
    return results

if __name__=="__main__":
    main()
