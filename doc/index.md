# Azure APIm Deployment Utils

Project Home Page:

[github.com/Haufe-Lexware/azure-apim-deployment-utils](https://github.com/Haufe-Lexware/azure-apim-deployment-utils)

## Introduction

In order to automate deployment to and from Azure API Management instances, we needed some kind of tooling to accomplish this. In many cases, the Azure Powershell Cmdlets will help you doing things, but in some cases, they just don't go far enough, and/or you want to deploy from a Linux/Mac OS X build agent/client.

We wanted to be able to accomplish the following things:

* Extract configuration from an API Management instance as far as possible, using the REST API and/or git Repository integration
* Push configurations to other APIm instances, using both the REST API and the git repository.
* Get simpler access to the APIm management and admin interfaces
  * Retrieving access tokens programmatically
  * Opening the Admin UI automatically (without going to the Azure Portal)

The python scripts at hand can do these things, mostly using the git integration, and the rest using the REST API (no pun intended).

#### Documentation Contents

The documentation consists of two parts (and a planned one): 

* A short tutorial on how to get started
* A more thorough documentation on how it works behind the scenes
* **Later**: Source code documentation

<a name="getting_started"></a>
# Getting started

In order to get started with the scripts, please first make sure you meet the [prerequisites](#prereqs). You can either [run the scripts using `docker`](#docker), or run them directly using your local Python interpreter. Using the docker image ensures that it will always work, disregarding of your operating system, so for running the scripts, docker is the recommended way.

**IMPORTANT**: When playing around with the scripts for the first time, always use a NON-PRODUCTION Azure APIm instance. This should be obvious though. Depending on what you do and try, the scripts will change your APIm configuration.

In order to get most out of this little "getting started" guide, you should make sure that you Azure APIm instance has the following things:

* Some property defined; you don't need to make use of it (yet), but having a property defined makes things easier to understand
* An uploaded client certificate (optional) to show how they can be manipulated
* At least one API definition of some kind

<a name="docker"></a>
## Getting started using `docker`

Make sure you have a recent version of Docker installed before continuing. The scripts and docker image was tested using Docker 1.10.3, so having this version or newer will most probably work without problems. If you encounter problems, please file an issue here on GitHub.

You can find the Docker Toolbox here: https://www.docker.com/products/docker-toolbox

#### Create an `instances.json` file

To get started, please create a new directory somewhere where you will put your configuration files. The first step is to create a new file called `instances.json` inside this newly created directory and fill in some data on the Azure APIm instance you want to work with.

Start with the sample file: [`sample-repo/instances.json`](sample-repo/instances.json):

```
{
    "apim": {
        "id": "the REST API tenant ID",
        "key": "The REST API Primary (or secondary) key",
        "url": "https://<your-apim>.management.azure-api.net",
        "scm": "<your-apim>.scm.azure-api.net",
        "host": <your-apim>.azure-api.net"
    }
}
```

For a detailed discussion on these properties, see the [`instances.json` documentation below](#instances). Later on, you will most probably use environment variables to fill in these values, but for getting started, you should fill in these values directly into your `instances.json` file.

#### Pull template configuration files from your APIm instance

The directory you created above is what is - for these scripts - called the *configuration directory* (*config dir*). This directory is used for all (at least most) operations on Azure APIm to decide which APIm instances is communicated with, and what will happen to it.

We will now create a one-off container from the base image and pass a command to it, which will extract some sample configuration files for us into that configuration directory. Start a "Docker Quickstart Terminal" if you haven't done that already, and issue the following command:

```
$ docker run -it --rm -v <path to config dir>:/apim haufelexware/azure-apim-deployment-utils extract_config all
```

**Behind a proxy?** If you are behind a proxy server, you will have to tell the container that by extending the command line like this:

```
$ docker run -it --rm -v <path to config dir>:/apim -e http_proxy=http://<your http proxy> -e https_proxy=https://<your https proxy> haufelexware/azure-apim-deployment-utils extract_config all
```

The `-it` command line switch tells Docker to run the container in the foreground, so that we see input and output from it. The `-v` switch maps a "volume" into the container, in this case we want to map the *config dir* into the container as the `/apim` directory inside the container. When using the dockerized scripts, this is always what you have to do to make the configuration known to the scripts. By using the `-e` switch, you may pass additional environment variables into the container, in this case to make the proxy servers known (if applicable).

Lastly, the `--rm` switch will clean up the container after use; we're only using `docker` here as a means to virtualize the environment in which the scripts run, and we don't have a need to keep the containers after they have finished running.

If everything runs as expected, you will see the following output:
```
$ docker run -it -v /Users/martind/Projects/tmp/apim2:/apim haufelexware/azure-apim-deployment-utils extract_config all
======================================
 EXTRACTING CONFIG FROM APIM INSTANCE
======================================
Property extraction succeeded.
Certificate extraction succeeded.
Swagger files extraction succeeded.
```

If you check your *config dir* now, you will notice the following things:

* Three new files have appeared:
  * `properties_extracted.json`
  * `certiticates_extracted.json`
  * `swaggerfiles_extracted.json`
* A new directory `local_swaggerfiles` has been created, containing one `json` Swagger file per API you have defined in your APIm instance.

#### Pushing a changed property

Now rename the `properties_extracted.json` file to `properties.json`. This means we declare it as *the real thing*, these are the properties we want to keep updated in our APIm instances. Open up the json file with your favorite editor and change value in it (you'll know what you can change in order not to destroy something).

Example content of the file:
```
{
    "SuperValue": {
        "secret": false, 
        "value": "This is a jolly fine property.", 
        "tags": [
            "sometag"
        ]
    }
}
```

Now we can push that change back up to your APIm instance again:
```
$ docker run -it --rm -v <path to config dir>:/apim haufelexware/azure-apim-deployment-utils update
```

If everything goes well, you will get an output similar to this:
```
$ docker run -it --rm -v /Users/martind/Projects/tmp/apim2:/apim haufelexware/azure-apim-deployment-utils update
========================
 UPDATING APIM INSTANCE
========================
Checking configuration...
Updating 'SuperValue'
Successfully updated property 'SuperValue' (id 56e03a98c8be1f0cb85a071c).
Update of properties succeeded.
Skipping certificates, could not find 'certificates.json'.
Skipping Swagger update, could not find 'swaggerfiles.json'.
```

Aha! So now we can change things from the command line. The last two lines also show you: Certificates and Swagger files can also be updated from the outside.

For a detailed description on how these files work, see the corresponding sections:

* [`certificates.json`](#certificates)
* [`swaggerfiles.json`](#swaggerfiles)
* [Updating an APIm instance](#apim_update)

#### Next steps

The next steps to do when working with the scripts can be the following:

* Replace the values of your properties with [environment variables](#env_variables), so that you can change them from the outside, e.g. for targeting different APIm instances
* Set up continuous integration of Swagger files from your backend service deployments, so that the Swagger definitions are automatically updated when the backend services have been deployed
* Integrate the scripts into your build pipelines, so that you can use them to propagate configurations from one APIm instance (Dev) to others (Test, Prod).

<a name="python"></a>
## Run locally using Python

Using the Python interpreter locally works equally well, as long as the prerequisites are fulfilled. The above guide applies in the same way, with the following differences:

Instead of doing a `docker ... extract_config`, in the directory containing the `.py` files, issue the following command:

```
C:\Projects\azure-apim-deployment-utils\> python.exe apim_extract_config.py <config dir> all
```

Likewise, the update command works in the same way:

```
C:\Projects\azure-apim-deployment-utils\> python.exe apim_update.py <config dir>
```

# Behind the scenes

### How does this work?

This is the principal idea how the scripts are intended to work:

![Deployment Paths](deployment_path.png)

In this picture you see three (point being: two or more) different instances of API Management which reflect the different stages of development of your API Management solution. In the documentation I will assume you have a three stage landscape (Dev, Test/Stage and Prod), but it is not limited to that. It does though only make sense to use the scripts if you are using more than one instance of Azure API Management instances, like this:

* **Dev** - a "Developer" instance of Azure API Management
* **Test/Stage** - may also be a "Developer" instance
* **Prod** - usually at least a "Standard" instance of API Management, even though the scripts will work with any type of instance.

An Azure API Management instance configuration consists of a lot of information, of which most is retrievable using the [`git` integration](https://azure.microsoft.com/en-us/updates/manage-your-api-management-service-instances-by-using-git/), but not all information is contained in the repository. Namely the following things are not included:

* Client Certificates for use for Mutual SSL connections to the backend
* Properties for parametrizing policy definitions

This means any deployment script needs to take care of these things in addition to just pushing the git configuration to a different instance. Fortunately, there is a REST API of Azure API Management which lets you do that, and this is also addressed by the scripts.

Additionally, all CRM content is (unfortunately) not contained in the git repository, but that part is **not** covered by the scripts (as the content is not available "from the outside").

#### From where do you typically use these scripts? (Use Cases)

##### Build environments

These deployment utility scripts are typically used within Build definitions, using some kind of build management tool. The only requirement on such a tool is that they must be able to trigger python scripts. Typical build tools are:

* [Team Foundation Build Service](https://msdn.microsoft.com/en-us/library/vs/alm/build/feature-overview)
* [ThoughtWorks go.cd](https://www.go.cd/)
* [Jenkins](https://jenkins-ci.org/)

The scripts being implemented in more or less plain vanilla Pyton 2.7.x enables you to choose any tool which allows you to run Python scripts.

**Remarks**:

* We at Haufe are using go.cd for automating builds. More information on this integration may follow in the future.
* This repository does (currently) **not** contain anything specific to a special build environment
* All parameters are assumed to be stored as environment variables, which is something all build environments tend to support quite easily out of the box. 

##### From the command line (developer tooling)

In some cases, the script may be useful simply for interacting with the Azure APIm instances, e.g. for [calling the Admin UI](#admin_ui) without havng to go via the Azure Portal, or doing manual extracts and deployments via the command line interface.

These use cases and/this functionality is described in the [utilities](#utilities) section.

##### As a base for other custom Python scripts

Using the [apim_core](#apim_core) module, you can also create other functionality based on the `AzureApim` class; it helps you create SAS tokens and such which are always needed when communicating with the REST API.

Also feel free to fork the repository and create pull requests in case you feel there is functionality which should be added.

#### What's in this package?

To get the expectations straight for these scripts: The scripts are intended to enable you to do **automatic deployments** to and from Azure API Management instances, but they can only provide a means for you to do this. Depending on your deployment scenarios, you will need different lego bricks to build up your pipelines.

In the following sections I will describe the deployment pipeline we have chosen you use, but your mileage may vary largely.

In case you have use cases you think are missing/the scripts do not reflect this, please open an issue so that we can discuss possible solutions.

#### Development principles

In order to get a good development experience when dealing with Azure API Management, you should follow some principles:

* Never hard code URLs, user names, passwords or any other sorts of credentials into your policies.
* Use properties for all these things.
* Design your API policies in such a way that they are instance independent; fight "we only need this for Prod" arguments
* Make use of Swagger imports, do not work with operation definitions, as they would be overwritten by the Swagger import anyway
* Automate as much as possible, definitely the following things:
  * Swagger imports
  * Configuration ZIP extracts

#### Development cycle

The following development cycle will with the Azure API Management in conjunction with these scripts:

1. Configure your "Dev" instance using the following means (not part of the scripts):
  * Manual policy configuration
  * API basic definitions
  * Swagger imports/updates
  * Property definitions
  * ...
2. Optionally (but recommended): Include an automated update of your API definitions via Swagger (covered by the scripts)
3. After each update (="build"), extract the configuration from the Dev instance into a ZIP archive (covered by the scripts)
4. At deployment time to Test (for your backend service), also deploy the API ZIP to your Test/Stage API Management instance (covered by the scripts)
5. When tests successfully finished, and right after you have deployed your backend services to Prod, use the very same ZIP file to deploy the configuration to your Prod APIm instance (with the scripts)

The difference between the deployments to the different APIm instances should ideally only lie within the configurable bits, i.e. in [certificates](#certificates) and [properties](#properties).  

### Consequences of automation

When deciding to automate the deployment of API definitions to Azure API Management, this will have some effects on how you need to design/implement policies. The following section describe some typical problems you encounter and the workarounds and/or patterns you can apply to achieve what you need.

<a name="service_url"></a>
#### Making the service URL configurable

A major pain point with the API definitions in Azure API Management is that it is not - out of the box - possible to parametrize the `serviceUrl` of an API (also known as the service backend URL). One would expect it to be possible to use a property to supply the URL, but unfortunately, this is not possible (using ``{{MyApiBackendUrl}}` is rejected for not being a proper URL).

The workaround for this is to use the `<set-backend-service>` policy on an API level, and there make use of a property.

**Example**:
```xml
<policies>
	<inbound>
		<base />
		<set-backend-service base-url="{{MyApiBackendUrl}}" />
	</inbound>
	<backend>
		<base />
	</backend>
	<outbound>
		<base />
	</outbound>
	<on-error>
		<base />
	</on-error>
</policies>
```

**Remember**: No hard coded URLs, user names and/or passwords inside your `git` repository, otherwise you'll be unhappy. All moving parts in certificates and properties only!

#### Automated updates of API definitions via Swagger

In order to update an API via its Swagger definition using the REST API (as opposed to the Web UI), it is necessary to know the *aid* (API ID) of the API to update. Finding this id is either a matter of pattern matching, or you need to define a unique ID which is both present in the APIm instance and on your own side.

To solve this problem, the scripts at hand chose to "abuse" the `serviceUrl` (see also above) to map the API to a Swagger definition. See section on the [`swaggerfiles.json`](#swaggerfiles) configuration file properties. This issue is described in more depth there.

<a name="prereqs"></a>
## Prerequisites

#### Running using `docker`

In order to run the scripts using `docker`, you will only need the following:

* A working `docker` host installation (1.10.3+),
* A `docker` command line interface, such as the "Docker Toolbox" for Windows or Mac OS X, or an actual Linux docker host.

#### Running using a local Python installation

In order to run the scripts, you will need the following prerequisites installed on your system:

* Python 2.7.x
* PIP
* The Python `requests` library: [Installation Guide](http://docs.python-requests.org/en/master/user/install/)
* The Python `gitpython` library: [Installation Guide](http://gitpython.readthedocs.org/en/stable/intro.html)
* `git` (available from the command line)


# Usage

Depending on the script you are using, the deployment scripts expect information from files residing in the same directory (referred to as the *configuration directory*). 

<a name="config_file"></a>
## Configuration directory structure

You can find a sample configuration repository inside the `sample-repo` directory. The following files are considered when dealing with an Azure API Management configuration:

* [`instances.json`](#instances): A file containing the `id`, `primaryKey` and other information on the Azure APIm instance to work with. It makes sense to get this information from environment variables, e.g. for use with build environments (which can pass information via environment variables).
* [`certificates.json`](#certificates): This file contains the certificates meta information which gives information on which certificates for use as client certificates when calling backend service are to be used. These certificates are subsequently to be used in authentication policies. See the sample file for a description of the file format.
* [`properties.json`](#properties): Properties to update in the target APIm instances. See the file for the syntax. Properties can be used in most policy definitions to get a parametrized behaviour. Typical properties may be e.g. backend URLs (used in `set-backend-service` policies), user names or passwords.
* [`swaggerfiles.json`](#swaggerfiles): Used when updating APIs via swagger files which are generated and/or supplied from a backend service deployment.
* [`docker_env.list`](#docker_env): A list of all [environment variables](#env_variables) used in all of the configuration files. This is used when passing environment variables from the `docker` host to the container.

<a name="env_variables"></a>
##### Using environment variables

In all configuration files, it is possible and advisable to make use of environment variables to inject information in the configuration files. Inside both properties (keys) and values, all strings starting with a dollar sign `$` are considered being environment variables. The environment variable reference is thus replaced with the content of the variable.

This is an important concept when using the scripts inside build environments: This is how you introduce differences between instances (Dev, Test, ..., Prod). In build environments, it is normally possible to define a set of environment variables "from the outside", and via this mechanism use the very same ZIP file for deployment into multiple instances (which is the purpose of the ZIP file). 

<a name="instances"></a>
### Config file `instances.json`

A sample file can be found in the sample repository: [`instances.json`](sample-repo/instances.json).

```json
{
    "apim": {
        "id": "$APIM_ID",
        "key": "$APIM_PRIMARY_KEY",
        "url": "$APIM_MGMT_URL",
        "scm": "$APIM_SCM_HOST",
        "host": "$APIM_GATEWAY_HOST"
    }
}
```

Inside the `instances.json` file you describe the Azure APIm instance you want to interact with using the scripts. These values can be found in the Azure APIm Admin UI, under "Security", and "API Management REST API". The check box "Enable API Management REST API" must be checked, which in turn shows the `id` ("Identifier") and an access key ("Primary Key" or "Secondary Key", both work), which has to be put in as `key`.

The property `url` has to provide the Management API URL, which is also stated on that page, under "Management API URL". If your APIm instance is called `myapim`, this will be `https://myapim.management.azure-api.net`.

As for the property `scm`, this has to point to the `git` repository of your API Management instance. If your APIm instance is called `myapim`, this will be `https://myapim.scm.azure-api.net`.

The last property, `host`, needs to point to the host name of your APIm Gateway (**not** the portal, the **Gateway**). If you have not customized this, this will be (using the same sample name as above) `https://myapim.azure-api.net`. If you have provided a custom domain for your API Gateway, supply the custom DNS entry here (as configured in the Azure Portal).

Note the use of [environment variables](#env_variables), which is not mandatory, but advisable.

The `instances.json` file is **mandatory**; without it, the scripts will not be able to resolve the target APIm instance.

<a name="certificates"></a>
### Config file `certificates.json`

A sample file can be found in the sample repository: [`certificates.json`](sample-repo/certificates.json).

```json
{
    "certificates": [
        {
            "fileName": "$APIM_CLIENT_CERT_PFX",
            "password": "$APIM_CLIENT_CERT_PASSWORD"
        }
    ]
}
```

In this file, you can provide client certificates which are to be used for communicating with your backend services (mutual SSL). You may provide a list of JSON objects, each containing a relative path filename (`fileName`) pointing to a PFX file, and the corresponding password (`password`). In order to use this with the `docker` image, the file name must be relative to the location of the `certificates.json` file, residing **below** the file (you **cannot** use `..` to go up). In consequence, your build scripts must put the PFX files inside a sub directory of the *config dir* for the update mechanism to find them.

This file is used in conjunction with the [`apim_update`](#apim_update) and [`apim_deploy`](#apim_deploy) scripts.

The scripts will compare the SHA1 fingerprints of the certificates present in the target APIm instance with what's inside the `certificates.json` file. If new certificates are detected, they will be inserted. If "unknown" certificates are found in the APIm instance, these certificates will be delete. The mechanism relies on the SHA1 fingerprint of the certificates to be unique.

When using this mechanism in conjunction with `apim_update` and/or `apim_deploy`, you will want to retrieve the PFX files and the corresponding passwords from a secure storage and pass in the location to the file via [environment variables](#env_variables), as is suggested in the sample above, too. **Note**: The secure storage/credential vault is **not** part of this script distribution.

The `certificates.json` file is **optional**. Without it, `apim_update` will not alter your certificate settings. Having an *empty* file will delete any certificates in your instance.

<a name="properties"></a>
### Config file `properties.json`

A sample file can be found in the sample repository: [`properties.json`](sample-repo/properties.json).

```json
{
    "BackendServiceUrl1": {
        "secret": false, 
        "value": "$APIM_BACKEND_1", 
        "tags": [
            "sometag"
        ]
    }, 
    "BackendServiceUrl2": {
        "secret": false, 
        "value": "$APIM_BACKEND_2", 
        "tags": []
    },
    "BackendClientCert": {
        "secret": true,
        "value": "$APIM_CERT_THUMBPRINT",
        "tags": [
            "certificate"
        ]
    }
}
```

The `properties.json` file contains a dictionary of properties, which each contain the following sub properties:

* `secret`: Is the property containing a secret/credential? If so, this means that it will not be displayed in the Admin UI. Defaults to `false`
* `value`: The value of the property; usually, this will be retrieved from an [environment variable](#env_variables) (see there for a discussion on usage); it may also be clear text.
* `tags`: Contains a (possibly empty) list of tags to associate with the property; this is only used for display purposes in the Azure APIm Admin UI and has no further impact on functionality.

The intended use of properties are for example the following:

* Setting behavioral switches, such as enabling or disabling logging
* Providing credentials to logging facilities, such as Azure Event Hubs
* Setting backend service URLs (albeit using the [`set-backend-url`](#service_url) policy)
* Other properties controlling instance specific things (please let me know if you have other use cases, I will add them here)

The `properties.json` file is **optional**. Without it, `apim_update` will not alter your properties settings. Having an *empty* file will delete any properties previously present in your instance.

<a name="swaggerfiles"></a>
### Config file `swaggerfiles.json`

A sample file can be found in the sample repository: [`swaggerfiles.json`](sample-repo/swaggerfiles.json).

```json
{
    "swaggerFiles":
    [
        {
            "serviceUrl": "https://v1.api1.domain.contoso.com",
            "swagger": "$APIM_SWAGGER_API1"
        },
        {
            "serviceUrl": "https://v1.api2.domain.contoso.com",
            "swagger": "$APIM_SWAGGER_API2" 
        }
    ]
}
```

The `swaggerfiles.json` is used by the `apim_update` script to update a list of APIs using their Swagger definitions.

The `swagger` properties must contain the relative path to the Swagger file to use for updating the API. The actual Swagger file must reside inside a sub directory of the *config dir* for the scripts to find them under all circumstances. This means your build scripts must put them there, if you do not decide to keep them in source control together with the script *config dir*. This is an option, but usually, your update build script would rather retrieve the Swagger files from a backend service drop location which is created at deployment of those backend services (that's the moment where the Swagger files are actually in effect).

When working locally with the Python interpreter, the `swagger` properties may as well be fully qualified paths, but when using the dockerized scripts, the path is mandatorily relative, as the container only sees the *config dir* and not the entire host.

This functionality is intended to be used after you have deployed your backend service to your Dev instances; the deployment scripts of your backend service (which in turn should supply the Swagger files) should trigger the `apim_update` script, which updates the API in your Dev APIm instance using the Swagger files.

Due to the fact that Azure APIm does not let us specify the service URL (`serviceUrl`) of an API using properties, which in turn could be used to uniquely identify an API, using these scripts require us to workaround this a little:

* In order to make the backend service URL configurable, you must use the [`<set-backend-url>` policy](#service_url)
* **Instead, we are using the `serviceUrl`, or "Web Service URL" (in the Admin UI) as an identifier of the API**

**Example**: APIs should be configured in such a way that the "Web Service URL" contains a URI-type identifier which - on a meta level - describes the service which lies behind the API:

![Using the serviceUrl as a unique identifier](api_service_url.png)

A naming schema for this may for example be: `https://<version>.<service name>.<yourcompany>.<tld>`, such as here `https://v1.service.contoso.com`. This is obviously a **fictional** URL which does not actually lead to the backend service. The backend URL is instead stored in a [suitable property](#properties) and used in a [`<set-backend-url>` policy](#service_url)

This is an ugly workaround for not being able to use a property in the `serviceUrl`. As soon as this limitation is lifted in Azure APIm, the `<set-backend-url>` policies can be removed, when using a property for the "Web Service URL".

The `swaggerfiles.json` file is **optional**; without it, `apim_update` will not update an APIs. Please note that the *absence* of this file or an entry into the file will **not** result in APIs being deleted from the updated instance. If you need to delete an API, you will have to do that either using the REST API directly and/or using PowerShell Cmdlets, or directly from the Admin UI.

##### Swagger import - Known problems

This section of the script implementation has the following known problems (as of March 16th 2016):

* **Do not use response or body schemas in your Swagger files**: If you use schema definitions using the `$ref` notation inside your Swagger files, these kinds of Swagger files will indeed *import* without error messages, but will not be able to *extract* and *deploy*  such APIs to other instances. This has the following background: The Swagger schema definitions are imported into your APIm instances and are also referenced in the API configuration files you can retrieve via git. But: The schema definitions themselves are **not** part of the git repository. This has the result that the `git` deployment fails due to missing schema definition references. The workaround for now is: Don't use schemas. **The APIm team knows of this and are currently working on a solution.**
* All other Swagger restriction described in the Azure APIm documentation

<a name="docker_env"></a>
### Config file `docker_env.list`

This file is only important when using the `docker` image to run the scripts. When dealing with build environments which use docker images to build things, the build agent itself (=the docker host) will get passed environment variables. These environment variables are (by docker default) **not** propagated to the containers actually running the scripts.

By using the `--env-file=<env var list>` command line switch of the `docker run` command, you can pass on a list of environment variables into the container; by simply stating the names of the environment variables in a list file, `docker run` will automatically pass through the value of the environment variable to the container.
Example file content:

```
# The list of environment variables for use in the container

# For instances.json
APIM_ID
APIM_PRIMARY_KEY
APIM_MGMT_URL
APIM_SCM_HOST
APIM_GATEWAY_HOST

# For certificates.json
APIM_CLIENT_CERT_PFX
APIM_CLIENT_CERT_PASSWORD

# For properties.json
APIM_CERT_THUMBPRINT
APIM_BACKEND_1
APIM_BACKEND_2

# For swaggerfiles.json
APIM_SWAGGER_API1
APIM_SWAGGER_API1
```

A sample file can be found in the [sample config repository](sample-repo/docker_env.list).

# Supported APIm operations

The following sections describe the operations which are supported out of the box by the scripts, in easily useful ways. For further support, it is quite simple to extend the scripts and/or add more scripts to support more things. Most other things which are not covered here are though already available using the PowerShell Cmdlets (link needed).

## Extracting template script configuration files

Using Python directly:
```
$ python apim_extract_config.py <config dir> <all|properties|certificates|swagger>
```

Using `docker`:
```
$ docker run -it --rm -v <config dir>:/apim haufelexware/azure-apim-deployment-utils extract_config <all|properties|certificates|swagger>
```

Use this functionality if you do not want to start from scratch creating configuration files. The script will create the following artefacts **inside the config dir**:

* `properties_extracted.json` (if `properties` or `all` was passed as one of the arguments)
* `certificates_extracted.json` (if `certificates` or `all` was passed as one of the arguments)
* `swaggerfiles_extracted.json` (if `swagger` or `all` was passed as one of the arguments)
* A directory `local_swaggerfiles` containing the current API Swagger definitions in your APIm instance (if passing `swagger` or `all` as one of the arguments)

You may also supply a combination of the three specific arguments, e.g. `properties swagger` to export properties and the Swagger files.

You can use these files as starting points when creating your own generic configuration files. Please note the following things:

* The properties contain clear text values; you will want to replace these with [environment variables](#env_variables)
* The entries in the `certificates_extracted.json` file are only *placeholders*; it is not possible to extract neither certificates nor the corresponding passwords from the APIm instance, these have to come from your build scripts/local files/environment variables
* The Swagger files which are extracted from the APIm instance *can* be used as a base for continued work, but usually you don't use these files (they're just for your information) but rather files which come from your backend service builds, where the Swagger files should serve as the service contract; they must be imported into APIm (the other way around) subsequently, automatically

<a name="apim_update"></a>
## Updating an APIm instance

Using Python directly:
```
$ python apim_update.py <config dir>
```

Using `docker`:
```
$ docker run -it --rm -v <config dir>:/apim --env-file=<env list file> haufelexware/azure-apim-deployment-utils update
```

The parameter `<config dir>` must point to directory containing configuration files as described in the [above sections](#config_file).

The `apim_update` script updates a (developer) instance of Azure API Management. The script will perform the following steps (in the given order):

1. Properties are updated according to the [`properties.json`](#properties) configuration file (if present).
1. Certificates are updated according to the [`certificates.json`](#certificates) configuration file (if present).
1. API definitions are updated according to the [`swaggerfiles.json`](#swaggerfiles) configuration file (if present).

Please note that this scripts uses only the REST API of the APIm instance to perform these updates.

##### Intended use of `apim_update`

The script `apim_update` is intended for use after a backend service has been deployed and after it has possibly updated its Swagger definition file. The deployment step of the backend service should automatically trigger an update of the APIm instance via this script. This should be done **automatically**, otherwise you may be at risk of forgetting to update the API definition.

It is advisable to subsequently do an [`apim_extract`](#apim_extract) to encapsulate the state of your APIm instance after the update. This ensures you can push this configuration to other (downstream) APIm instances, like Test, or Prod.

**Note**: The scripts assume you know what you are doing in terms of compatible changes of your API (evolvability, version compatibility). For guidelines on how to accomplish this, please refer to API Styleguides, for example the [Haufe-Lexware API Styleguide](http://dev.haufe-lexware.com/resources/).

<a name="apim_extract"></a>
## Extracting a configuration ZIP file

Using Python directly:
```
$ python apim_extract.py <config dir> <target zip file>
```

Using `docker`:
```
$ docker run -it --rm -v <config dir>:/apim --env-file=<env list file> haufelexware/azure-apim-deployment-utils extract [target zip file]
```

The command will create a ZIP file `<target zip file>`, or, in the `docker` case, the file `apim_extract.zip` inside the *config dir*. This configuration archive contains the following things:

* The [config files](#config_file)
* The complete `git` APIm repository, reflecting the APIm configuration (groups, policies, API definitions,...)

This is intended to be a complete blueprint of an Azure APIm instance which can be used with the [deployment script](#apim_deploy) to deploy it to a different APIm instance.

Please note the following things:

* The ZIP archive does **NOT** contain
    * Swagger files (only the `swaggerfiles.json`)
    * Certificate files (only the `certificates.json`)
* In order to be deployable to another APIm instance, the configuration files need to be parametrized using [environment variables](#env_variables)

## Deploying a configuration ZIP file (to a different APIm instance)

Using Python command line:
```
$ python apim_deploy.py <source config zip>
```

Using `docker`:
```
$ docker run -it --rm -v <path to zip file>:/apim --env-file=<path to docker_env.list> haufelexware/azure-apim-deployment-utils deploy <source config zip> 
```

Deploys a ZIP file which was extracted via ["Extract"](#apim_extract) to another (or the same) APIm instance. In this case, the *config dir* is extracted from the ZIP file, and the values are subsequently used from there. In the `docker` case, the `<source zip>` must be a file name inside the `<path to zip file>`. If you need certificates, these are also expected to lie as files beneath the `<path to zip file>`, e.g. like this:

* `D:\BuildFiles\`
    * `apim_extract.zip`
    * `local_certificates\` (directory)
        * `cert1.pfx`
        * `cert2.pfx`
        * ...

The content of the configuration files need to point to the certificate files accordingly; this is usually done by defining environment variables accordingly, or by standardizing the file names.

This command deploys an Azure APIm configuration into an Azure APIm instance by doing the following steps:
1. Extract the *config dir* files into a temporary directory
2. Update properties in the target APIm instance
3. Update certificates in the target APIm instance
4. Deploy the `git` repository content from the archive ZIP using `git` to the target APIm instance

**Please note** that the `swaggerfiles.json` is not used when deploying using this script. This is not needed, as the entire API definition is already contained within the `git` repository, which in turn is deployed. The `swaggerfiles.json` are only used for deploying new source Swagger file changes on the Dev instance!

##### Special case deleted 'loggers'

... can't be removed in the same step as they are removed from the policies. Two-step deployment (call it a bug of APIm if you want).

##### Special case deleted properties

... can't be removed in the same step as they are removed from the policies. Two-step deployment needed.

##### Special case deleted certificates

... can't be removed in the same step as they are removed from the policies. Two-step deployment needed.

<a name="utilities"></a>
## Utility functions

<a name="admin_ui"></a>
### Opening Admin UI (without Azure Portal)

```
$ python apim_open_apim_ui.py <config dir> [<instance>]
```

Opens a web browser pointing to the Admin Portal of your Azure API Management instance, without going via the Azure Classic Portal.

This does not make sense using `docker`, but you may use the [`token` command](#token) described below to achieve a similar effect if needed.

### Generate PFX/PKCS#12 Thumbprint from file

Using Python command line:
```
$ python apim_openssl.py <certificate.pfx> <password>
```

Using `docker`:
```
$ docker run -it --rm -v <path to zip file>:/apim --env-file=<path to docker_env.list> haufelexware/azure-apim-deployment-utils pkcs12_fingerprint <certificate.pfx> <password>
```

Outputs the PFX thumbprint of a certificate file; useful when scripting things. Use this in order to set environment variables which in turn can be used inside properties, e.g. when specifying which certificate should be used for mutual authentication scenarios.

<a name="token"></a>
### Generate various access tokens for debugging and developing

Using Python command line:
```
$ python token_factory <config dir> <sas|git|adminurl>
```

Using `docker`:
```
$ docker run -it --rm -v <path to zip file>:/apim --env-file=<path to docker_env.list> haufelexware/azure-apim-deployment-utils token <sas|git|adminurl>  
```

* `sas`: Generates a Shared Access Signature (SAS) for use in the `Authorization` header when calling the Azure APIm REST API, useful for testing and debugging the APIm REST API
* `git`: Generates a git password for use with the Azure APIm `git` repository; actually, it will return an entire `git clone` command line you can just copy and paste
* `adminurl`: Generates an URL you can copy and paste into a browser to open up the Admin UI of your Azure APIm instancea (this is also used in the [Opening Admin UI](#admin_ui) script)

# Appendix

## Further Reading

Links to the Azure APIm documentation:

* ...
