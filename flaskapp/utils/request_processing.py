def get_metadata(request, app):
    model_params = {}
    for qs_name, qs_value in request.args.items():
        if qs_name not in ['user']:
            model_params[qs_name] = qs_value

    model_params['user_id'] = request.args.get('user', -1)

    # App name
    model_params['app_name'] = app

    # Do we want to autopredict?
    model_params['predict'] = request.args.get('predict', True)

    # Model name to use in prediction
    model_params['model'] = request.args.get('model', 'all')

    # Current file
    model_params['idx'] = request.args.get('idx')

    # Total files
    model_params['total'] = request.args.get('total')
    return model_params
