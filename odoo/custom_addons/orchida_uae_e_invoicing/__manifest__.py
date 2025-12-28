{
    'name': 'Orchida Soft UAE E-Invoicing Module',
    'version': '18.0.1.0.0',
    'summary': 'Send invoice to API when validated',
    'description': """
        This module automatically triggers an API call when an invoice is validated.
        It is standardized and reusable across projects.
    """,
    'author': 'Orchida-Soft',
    'website': 'https://orchida-soft.com',
    'depends': ["base","account"],
    'data': [
        'security/ir.model.access.csv',
         'views/api_sent_invoice_view.xml',
          'views/e_invoice_config_form.xml',
           'views/res_partner_view.xml',
            'views/res_company_view.xml',

        
        'views/menuitems.xml'
    ],


    
    'images': [
        'images/main_screenshot.png',
        
    ],


    'installable': True,
    'application': True,
    "license": "LGPL-3",

}