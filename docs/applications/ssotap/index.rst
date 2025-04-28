.. px-app:: ssotap

#####################################################
ssotap — IVOA DP03 Solar System Table Access Protocol
#####################################################

SSOTAP (SSO Table Access Protocol) is an IVOA_ service that provides access to the ObsCore table which is hosted on postgres.
On the Rubin Science Platform, it is provided by https://github.com/lsst-sqre/tap-postgres, which is derived from the `CADC TAP service <https://github.com/opencadc/tap>`__.
This service provides access to the Solar System tables that are created and served by the butler.

The TAP data itself, apart from schema queries, comes from Postgres.
The TAP schema is provided by images built from https://github.com/lsst/sdm_schemas.

.. jinja:: tap
   :file: applications/_summary.rst.jinja

Guides
======

.. toctree::

   values
