# Press Setup

### Configuration

1. Press Settings

- #### Domain
    Domain (can also be a subdomain) used as suffix for all things press.
 
    e.g. If domain is set as `example.com` then servers will have names like `f1.example.com`, `m1.example.com`, etc. sites will have urls like `magical.example.com`

    **Note:** It is necessary to have access DNS settngs to this domain.

- #### Bench Configuration
    Following keys must be added, rest is up to you.
    ```JSON
        "dns_multitenant": true,
    {
        "frappe_user": "frappe",
        "monitor": true
    }
    ```

- #### DNS
    DNS Provider: Only AWS Route53 is supported as of now.

    AWS Access Key ID and AWS Secret Access Key can be acquired from AWS Console.

    **Note**: Server setup won't work without this.

- #### TLS
    EFF Registration Email: Provide a valid email. Let's Encrypt will send notifications to this email.

    Certbot Directory: Certbot will use this directory to store certificates, configuration logs etc. 

    e.g. `/home/frappe/.certbot`

    Webroot Directory: 
    Certbot will use this directory to place the verification file. It'll be created if it doesn't exist.

    e.g. `/home/frappe/.certbot/webroot`

    Note: TLS for custom domains doesn't work for local setup. In which case this is pointless.

    **Note:** Make sure frappe user owns both these directories. They'll be created if they doesn't exist.

- #### Stripe
    Create a Stripe Settings

    Publishable Key and Secret Key can be acquired from Stripe Dashboard.



### ToDo
A lot of stuff
