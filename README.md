# nanobox-adapter-libcloud
A Nanobox cloud provider adapter to integrate with multiple cloud providers

## Required evars
In order to grab catalog data, default credentials are required for each supported provider. These creds will never be used to actually create/manage actual VMs, as the internal logic will never even look them up outside of the one scenario where catalog data is being generated. Still, it's a lot of variables to set, so they'll all be listed below, to ensure they all get added in. Since there are non-auth evars required as well, the sensitive ones are marked, below, with an asterisk (\*).

### Google Compute Engine
-   `GCE_SERVICE_EMAIL`\*
-   `GCE_SERVICE_KEY`\*
-   `GCE_PROJECT_ID`\*
-   `GCE_MONTHLY_DISK_COST`
-   `GCE_MONTHLY_SSD_COST`

## Et Cetera
More info will be added to this README as it comes up.
