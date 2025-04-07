def merge_dicts(dict1, dict2, *args, **kwargs):
    """
    Recursively merge dictionaries.

    Parameters
    ----------
    dict1 : dict
        First dictionary to merge
    dict2 : dict
        Second dictionary to merge
    *args : dict
        Additional dictionaries to merge
    **kwargs : dict
        Additional parameters:
        - overwrite: bool, default=False
          If True, values from later dictionaries will overwrite those from earlier ones
          If False, values from earlier dictionaries will be kept

    Returns
    -------
    dict
        A new dictionary containing the merged key-value pairs
    """
    overwrite = kwargs.get("overwrite", False)
    result = dict1.copy()

    dicts_to_merge = [dict2] + list(args)
    for d in dicts_to_merge:
        for k, v in d.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = merge_dicts(result[k], v, overwrite=overwrite)
            elif k not in result or overwrite:
                result[k] = v

    return result
