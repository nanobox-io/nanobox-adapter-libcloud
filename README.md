# nanobox-adapter-libcloud
A Nanobox cloud provider adapter to integrate with multiple cloud providers

## Required evars
In order to grab catalog data without a user's cedentials (for generic pricing
estimates, for example), default credentials are required for each supported
provider. These creds will never be used to actually create/manage actual VMs,
as the internal logic will never even look them up outside of the one scenario
where catalog data is being generated for generic use. Still, it's a lot of
variables to set, so they'll all be listed below, to ensure they all get added
in. Since there are non-auth evars required as well, the sensitive ones are
marked, below, with an asterisk (\*).

_Please keep this list sorted alphabetically by provider name to help with
finding evars quickly._

### Amazon AWS EC2
-   `EC2_KEY_ID`\*
-   `EC2_ACCESS_KEY`\*

### Google Compute Engine
-   `GCE_SERVICE_EMAIL`\*
-   `GCE_SERVICE_KEY`\*
-   `GCE_PROJECT_ID`\*
-   `GCE_MONTHLY_DISK_COST`
-   `GCE_MONTHLY_SSD_COST`

### Microsoft Azure Classic (Experimental)
-   `AZC_SUB_ID`\*
-   `AZC_KEY`\*

### Microsoft Azure Resource Manager
-   `AZR_SUBSCRIPTION_ID`\*
-   `AZR_TENANT_ID`\*
-   `AZR_APPLICATION_ID`\*
-   `AZR_AUTHENTICATION_KEY`\*
-   `AZR_CLOUD_ENVIRONMENT`\* (optional)

### OVH
-   `OVH_APP_KEY`\*
-   `OVH_APP_SECRET`\*
-   `OVH_CONSUMER_KEY`\*
-   `OVH_PROJECT_ID`\*
-   `OVH_APP_REGION`\*

### Packet
-   `PKT_API_KEY`\*

### Scaleway
-   `SCALEWAY_ACCESS_KEY`\*
-   `SCALEWAY_API_TOKEN`\*

### Vultr
-   `VULTR_API_KEY`\*

## Development Usage
Start the adapter by running `nanobox run gunicorn -c /app/etc/gunicorn.py
nanobox_libcloud:app` in a terminal. If you're working on one or more providers
that use background tasks (currently only Azure), also start celery, by running
`nanobox run celery -A nanobox_libcloud.celery worker -E -l info` in a second
terminal. Access [the adapter root](http://adapter.local/) for further usage
info.

## Et Cetera
More info will be added to this README as it comes up.
