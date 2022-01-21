# copy-aws-rds-parameter-group
Copy an aws rds parameter group across regions

Original file sopied from https://gist.github.com/phill-tornroth/f0ef50f9402c7c94cbafd8c94bbec9c9.

Run as `python3 cp_parameter_group.py us-east-1:params1 eu-central-1:params1`.

Keep in mind that some parameter values are likely to cause problems, even if they are the system default. If this happens skipp all those by adding them to `IGNORE_PARAMETERS_NAME`
constant and rerun, until no errors reported. If you have at least one value that caused a problem, it is likely that your settings are not cloned properly. 

Keep the constant `IGNORE_PARAMETERS_NAME` that you observed gave a run without any problems, delete the parameter group in the target region and rerun.

Finally verify manually that the new group definitions seem identical to the origin. 
