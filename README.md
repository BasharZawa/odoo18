## Writing importable module:

## To turn on the venv environment:
source venv/bin/activate

## To scaffold new module
./odoo-bin scaffold your_app_name addons_path


## development for long
UPDATE ir_config_parameter
SET value = gen_random_uuid()
WHERE key = 'database.uuid';