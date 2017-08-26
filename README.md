# nanobox-adapter-libcloud
A Nanobox cloud provider adapter to integrate with multiple cloud providers

## Required evars
In order to grab catalog data, default credentials are required for each supported provider. These creds will never be used to actually create/manage actual VMs, as the internal logic will never even look them up outside of the one scenario where catalog data is being generated. Still, it's a lot of variables to set, so they'll all be listed below, to ensure they all get added in.

### Google Compute Engine
-   `GENERIC_GCE_CLIENT_ID`
-   `GENERIC_GCE_CLIENT_SECRET`
-   `GENERIC_GCE_PROJECT_ID`

## Et Cetera
More info will be added to this README as it comes up.
