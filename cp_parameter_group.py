
"""
 Copies a parameter group in RDS, particularly useful for doing cross-region copies (which AWS documents,
 but doesn't actually support at the time of this writing.
 Usage:  python cp-parameter-group.py us-west-1:lookerdb-56 us-west-2:lookerdb-56
"""
# forked from https://gist.github.com/phill-tornroth/f0ef50f9402c7c94cbafd8c94bbec9c9

import boto3
from botocore.exceptions import ClientError
import sys
import difflib
import json

IGNORE_PARAMETERS_NAMES = ()

def chunks(sequence, chunk_size):
    """
     Yields the sequence as a sequence of sequences size chunk_size (or fewer,
     in the case of the last chunk). Guarantees delivery of everything (as
     opposed to strategies that leave elements off of the end when
     len(sequence) % chunk_size != 0
    """
    start = 0
    while start < len(sequence):
        end = start + chunk_size
        yield sequence[start : start + chunk_size]
        start = end


def get_params_for_client(client, param_group_name, filter_lambda=None):
    if filter_lambda is None:
        filter_lambda = lambda x: True
    ret_parameters = []
    parameters_response_marker = None
    while True:
        describe_db_parameters_kwargs = dict(DBParameterGroupName=param_group_name, MaxRecords=100)
        if parameters_response_marker is not None:
            describe_db_parameters_kwargs['Marker'] = parameters_response_marker
        source_parameters_response = client.describe_db_parameters(**describe_db_parameters_kwargs)
        source_parameters_response_parameters = [p for p in source_parameters_response['Parameters'] if filter_lambda(p) and p['ParameterName'] not in IGNORE_PARAMETERS_NAMES]
        ret_parameters.extend(source_parameters_response_parameters)
        if 'Marker' not in source_parameters_response:
            print(f"found {len(ret_parameters)} params")
            break
        else:
            parameters_response_marker = source_parameters_response["Marker"]
    return ret_parameters



# region:parameter_name
if __name__ == '__main__':
    source_region, source_name = sys.argv[1].split(":")
    source_client = boto3.client("rds", region_name=source_region)
    source_summary = source_client.describe_db_parameter_groups(DBParameterGroupName=source_name)
    source_family = source_summary["DBParameterGroups"][0]["DBParameterGroupFamily"]
    source_description = source_summary["DBParameterGroups"][0]["Description"]
    source_parameters = get_params_for_client(source_client, source_name, filter_lambda=lambda p: p["IsModifiable"] and "ParameterValue" in p)

    target_region, target_name = sys.argv[2].split(":")
    target_client = boto3.client("rds", region_name=target_region)
    groups_in_target_region = set(
        [
            g["DBParameterGroupName"]
            for g in target_client.describe_db_parameter_groups()["DBParameterGroups"]
        ]
    )

    if target_name not in groups_in_target_region:
        target_client.create_db_parameter_group(
            DBParameterGroupName=target_name,
            DBParameterGroupFamily=source_family,
            Description=source_description,
        )
        print(f"Created param group {target_name} in region {target_region}")

    # AWS limits parameter modifications to 20 at a time
    for parameters in chunks(source_parameters, 20):
        try:
            target_client.modify_db_parameter_group(
                DBParameterGroupName=target_name, Parameters=parameters
            )
        except ClientError:
            print(parameters)
            # check what is wrong. Maybe put these in IGNORE_PARAMETERS_NAMES or deal with them in a special way
            raise
        for parameter in parameters:
            print("%s = %s" % (parameter["ParameterName"], parameter["ParameterValue"]))

    all_params_for_source = get_params_for_client(source_client, source_name, filter_lambda=None)
    all_params_for_target = get_params_for_client(target_client, target_name, filter_lambda=None)
    diff_str_list = [li for li in difflib.ndiff(json.dumps(all_params_for_source, sort_keys=True, indent=4), json.dumps(all_params_for_target, sort_keys=True, indent=4)) if li[0] != ' ']
    if len(diff_str_list) > 0:
        raise ValueError(f"found differences in params: {diff_str_list}")

    print("Complete.")
