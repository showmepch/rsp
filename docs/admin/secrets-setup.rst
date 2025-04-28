#########################
Set up secrets management
#########################

Phalanx requires its secrets be stored in Vault in a specific structure, but is otherwise able to work with a variety of Vault configurations.
Phalanx does, however, come with tools to manage one specific approach to using Vault, so you may want to follow that design unless you have other requirements.

This document explains the basic structure of how secrets must be stored in Vault, describes the tools for managing that structure, and describes the optional tools for managing Vault authentication credentials and paths for one specific Vault design.

If you are setting up an environment that will be running a 1Password Connect server for itself, you will need to take special bootstrapping steps.
See :px-app-bootstrap:`onepassword-connect` for more information.

.. note::

   The environments :px-env:`base` and :px-env:`summit` are still using an old secrets management system that sometimes used multiple secrets per application and sometimes pointed multiple applications at the same secret.
   New enviroments should use the system described here, but be aware that you will see remnants of the old system lingering in application configuration.

   For documentation of how to convert an existing environment to the new secrets management system, see :doc:`migrating-secrets`.

Basic Vault structure
=====================

Every Phalanx environment must have a corresponding "path" inside the Vault database.
Conventionally, this is :samp:`secrets/phalanx/{environment}`, where the initial ``secrets`` component is the mount point for the KV v2 secrets engine.
However, it can be anything you choose if, for instance, you have an existing Vault with its own conventions.

This must be a KV v2 secrets store.
Phalanx currently does not support other secrets engines.

Under that path, Phalanx expects one Vault secret per application, plus optionally an additional secret named ``pull-secret``.
The name of each secret other than ``pull-secret`` matches the name of the application.
So, for example, all secrets for Gafaelfawr for a given environment may be stored as key/value pairs in the secret named :samp:`secrets/phalanx/{environment}/gafaelfawr`.

This path is configured for each environment via the ``vaultPathPrefix`` setting in the environment :file:`values-{environment}.yaml` file.
The URL to the Vault server is set via the ``vaultUrl`` setting in the same file and defaults to the SQuaRE-run Vault server.

.. _admin-vault-credentials:

Vault credentials
=================

A running Phalanx environment must have read access to all Vault secrets under its secrets path.
This is normally done by creating a `Vault AppRole`_ that has read access to that path and providing its credentials to :px-app:`vault-secrets-operator`.

.. _Vault AppRole: https://developer.hashicorp.com/vault/docs/auth/approle

Phalanx does not strictly require this approach.
any authentication approach that `Vault Secrets Operator`_ supports may be used as long as :px-app:`vault-secrets-operator` is configured accordingly for that environment.
However, the standard installation process only supports AppRoles, and tooling is provided to manage those roles.

Phalanx environment administrators, but not the running Phalanx environment, must also have access to a Vault write token with permissions to create, update, and delete secrets under the Vault path for that environment.
This must be a write token, not any other Vault authentication method, in order to use the standard Phalanx tools.

It is possible to maintain a Phalanx environment without this write token, but this will require administrators manually set all required secrets in Vault, including generated secrets.
This process will be tedious and error-prone and is not supported.
Using a Vault write token and the standard Phalanx tools is therefore strongly recommended.

Maintaining Vault credentials
-----------------------------

Phalanx provides a tool to create appropriate read Vault AppRoles and write tokens with correct ACLs.
This tool is used by SQuaRE to manage its Vault server.
Use of this tool is optional.

These commands must be run with the environment variable ``VAULT_TOKEN`` set to a token with access to create and update policies, list token accessors, list AppRole SecretIDs, create and update AppRoles, revoke AppRole Secret IDs, and create and revoke tokens.
This normally requires a Vault admin or provisioner token or some equivalent.

:samp:`phalanx vault create-read-approle {environment}`
    Creates a new Vault AppRole with read access to the Vault secrets path for the given environment.
    If any such AppRole already exists, it is updated with appropriate policies and any existing SecretIDs are revoked.
    The output includes the RoleID and SecretID for the AppRole, which can then be provided to `Vault Secrets Operator`_.
    The optional ``--as-secret`` flag may be provided to write the AppRole credentials in a form suitable for piping to :command:`kubectl apply` to create a secret for `Vault Secrets Operator`_.

    When creating an AppRole for GitHub Actions (usually the :px-env:`minikube` environment), pass ``--token-lifetime 3600`` to this command to limit the maximum token lifetime to an hour.
    This avoids accumulating AppRole tokens in Vault that slow down other Vault operations.

:samp:`phalanx vault create-write-token {environment}`
    Creates a new Vault token with write (create, update, and delete) access to the Vault secrets path for the given environment.
    If any write token previously created by :command:`phalanx` already exists, it is revoked.
    The output includes the new Vault token, which you should save somewhere secure where you store other secrets.
    (The running Phalanx environment does not need and should not have access to this token.)
    You will later set the environment variable ``VAULT_TOKEN`` to this token when running other :command:`phalanx` commands.

    For SQuaRE-managed environments, always update the ``Phalanx Vault write tokens`` 1Password item in the SQuaRE 1Password vault after running this command.
    Also store this token in the ``vault-write-token`` key of the 1Password vault for this environment.
    See :ref:`admin-onepassword-vault-token` for more details.

:samp:`phalanx vault audit {environment}`
    Check the authentication credentials created by the previous two commands in the given environment for any misconfiguration.
    This will also check if the write token is expired or about to expire.

Secret types
============

Phalanx secrets can be divided into two basic types.

**Static secrets** are those that must be provided by some external source.
They are primarily secrets used to talk to some external service, such as GitHub tokens or Slack web hook URLs.
The administrator of an environment must determine the values of all required static secrets and provide those secrets to Phalanx in some way.
This is discussed further in :ref:`admin-static-secrets`.

**Generated secrets** are secrets that can be automatically generated during installation of an environment.
This includes secrets that are set to random strings during an installation or reinstallation of the environment, generated private X.509 keys or other cryptographic keys, secrets that are copied into one application from another application, and secrets that are set to a static value for all environments (required sometimes by third-party charts).

Part of setting up a new Phalanx environment is providing all the required static secrets, generating all of the generated secrets, and putting the resulting secret values into Vault where they can be retrieved by the `Vault Secrets Operator`_ installation for that environment.
This is done with the various :command:`phalanx secrets` commands, described below.

Secrets are specified by :file:`secrets.yaml` files for each application.
For more details, see :doc:`/developers/secrets-spec`.

.. _admin-static-secrets:

Static secret sources
=====================

Static secrets are secrets that cannot be randomized or generated according to some algorithm.
They must be provided by an administrator, usually because they are shared secrets with some service external to Phalanx, such as GitHub or Google.
A critical part of maintaining a Phalanx environment is providing and managing the static secrets for that environment.

The :command:`phalanx` command-line tool supports three ways to provide static secrets: a YAML file, 1Password, and maintaining the secrets directly in Vault.

.. _admin-secrets-yaml:

Static secrets from a YAML file
-------------------------------

All the static secrets for a Phalanx environment can be provided in a YAML file.
To create a template for that YAML file, run:

.. prompt:: bash

   phalanx secrets static-template <environment>

Replace ``<environment>`` with the name of the environment.
This will print a template for the required static secrets to standard output.

Then, store this file in a secure location and fill in the ``value`` keys and, if necessary, the ``pull-secret`` block with the appropriate values.
You can, if you choose, also store the Vault write token for your environment in this file, which will allow you to skip setting the VAULT_TOKEN environment variable each time you want to run a :command:`phalanx secrets` command.

You will provide this file to :command:`phalanx` when performing secret sync or audit operations (see :doc:`sync-secrets`) with the ``--secrets`` command-line flag.

.. _admin-secrets-onepassword:

Static secrets from 1Password
-----------------------------

Static secrets may be stored in a 1Password vault.
In this case, each application with static secrets should have an entry in this 1Password vault.

The 1Password vault must be served by a 1Password Connect server so that the Phalanx tooling can access the secrets.
See :px-app:`onepassword-connect` for more details on how this is done.

Application secrets
^^^^^^^^^^^^^^^^^^^

All entries should be of type :menuselection:`Server` with all of the pre-defined sections deleted.
Each key and value pair within that entry corresponds to one secret for the application, with the key matching the key of that secret.
Fields should be marked as passwords when appropriate for their 1Password UI semantics, but Phalanx will read the secret value without regard for the type of field.

To see what secrets must be provided in 1Password, generate the same YAML template as you would when providing secrets in a YAML file.

.. prompt:: bash

   phalanx secrets static-template <environment>

Replace ``<environment>`` with the name of your environment.

The keys under applications are the names of applications and should be the name of a 1Password vault entry.
The next-level key should be used as the key of a field in that entry.
Fill in the value with the value of that secret.

.. _admin-onepassword-pull-secret:

Pull secret
^^^^^^^^^^^

If the environment needs a pull secret, create a 1Password item of type :menuselection:`Server` and title ``pull-secret``.
Delete all of the pre-defined sections.
Then, for each Docker registry used by that environment that requires a pull secret, create a section whose name is the FQDN of the registry.
Within that section, add two fields with labels ``username`` and ``password`` and containing the Basic Auth credentials for that registry.
The type of the ``password`` field should be changed to password.

This will be transformed into a Vault entry in the correct format for generating a ``Secret`` resource in Kubernetes that can be used as a pull secret.

.. _admin-onepassword-vault-token:

Vault write token
^^^^^^^^^^^^^^^^^

The Vault write token for the environment can also be stored in 1Password.
If you do this, you will not have to set the VAULT_TOKEN environment variable before :doc:`auditing <audit-secrets>` or :doc:`syncing <sync-secrets>` secrets.

To do this, create a 1Password item of type :menuselection:`Server` and title ``vault-write-token``.
Delete all of the pre-defined sections.
Then, create an entry with key ``vault-token`` and value set to the Vault write token for this environment (normally created with :command:`phalanx vault create-write-token`).
Don't forget to change the type of the field to password.

Configuring 1Password support
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For an environment to use 1Password as a static secrets source, there must be a 1Password Connect server that serves the secrets for that environment from a 1Password vault.
See :doc:`/applications/onepassword-connect/add-new-environment` for details on how to enable a new 1Password Connect server for your environment using Phalanx.

When running :command:`phalanx secrets` to sync or audit secrets, you will need to set ``OP_CONNECT_TOKEN`` to the read token for that 1Password Connect server.
For SQuaRE-run environments, you can get that secret from the 1Password item ``RSP 1Password tokens`` in the SQuaRE 1Password vault.

Static secrets from Vault
-------------------------

Finally, you can simply maintain static secrets directly in Vault.

If you do not provide any other source of static secrets for an environment, and the static secret already exists in Vault, the :command:`phalanx secrets` command will use that existing value.
Therefore, if you wish, you may manually set the secrets directly in Vault (or use some other Vault integration beyond the scope of this document) and not provide Phalanx with any other static secrets source.

If you take this approach with an environment that requires a pull secret, you will need to create a Vault secret with the name ``pull-secret`` containing one key named ``.dockerconfigjson``.
The contents of that key must be the JSON-serialized authentication information for the Docker registries that require authentication.
See `Pull an image from a private registry <https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/>`__ in the Kubernetes documentation for more details about the correct format.

Syncing secrets
===============

Finally, before installing a Phalanx environment, you will need to perform the initial secrets sync.

Secrets syncing is an operation that can be done repeatedly.
There is nothing that special about the first run except that it will have more to do.
You can therefore follow the :doc:`normal secrets syncing procedure <sync-secrets>` for the first secrets sync.

Next steps
==========

- Now that you've defined the secrets for your environment, you're ready to do the initial installation: :doc:`installation`
