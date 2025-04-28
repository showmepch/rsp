##########################################################
Kubernetes kubelet nodeStatusMaxImages setting for Nublado
##########################################################

The image prepuller in the :px-app:`nublado` application requires Kubernetes to keep track of a number of images and ensure each of those images are present on every node.  This is required in order to provide a pleasant user experience, because the ``sciplat-lab`` images are large and typically take 3-5 minutes to pull and unpack when they are not already present on a node.
The default Kubernetes settings can in some circumstances result in the :px-app:`nublado` failing to display images in its spawner menu, as well as the image prepuller running continuously.

Setting nodeStatusMaxImages
===========================

The solution, described here, is to set the ``nodeStatusMaxImages`` in the Kubernetes cluster's `kubelet config`_.

.. _`kubelet config`: https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/

The recommended remediation is to disable each node's cap on ``nodeStatusMaxImages`` by setting its value to ``-1`` in the node's kubelet configuration file.  Typically this file is found at ``/var/lib/kubelet/config``.  However, your Kubernetes deployment may have relocated it, you may be using a drop-in configuration directory, or you may be managing it with some other automation tool.

After editing the configuration file, you must then restart kubelet on each node.

Background
==========

The fundamental problem is that the Kubernetes setting ``nodeStatusMaxImages`` is set to 50 by default.  The only way to retrieve a list of which images are present on a node is to query the node, and look through its ``status.images`` information.

In general, the Nublado prepulling strategy relies on the supposition that prepulled images are the freshest; that, eventually, people will stop using old images; and finally, when the disk pressure garbage collection threshold is exceeded, the images that have not been used in the longest time will be purged.

When the ephemeral storage is sized such that there is not room for very many ``sciplat-lab`` images (but enough space to hold at least the full set that should be prepulled), and when ``sciplat-lab`` is the most common image found on nodes, this generally just works with no further attention: the menu stays populated with the current images, and since they are prepulled, they spawn quickly when selected.
Disk pressure cleans up outdated images, and everything works as it should.

However, if the node has a large amount of ephemeral storage, and/or there is much non-Lab application use on the node, this can cause a problem for the prepuller: it is entirely possible for images that are indeed present on the node to not be in the first fifty images in the image list, and therefore not to be found when the prepuller determines which images need prepulling.

This has two consequences: first, the prepuller will be constantly scheduling images as it prepulls the ones it wants, because even though the image is already resident on the node, the prepuller does not, and cannot, know that.
Second, these images, because the prepuller incorrectly believes they are not resident on all nodes, will not be visible in the JupyterHub spawner menu, although they will be available from the dropdown list.

Fortunately there is a simple fix: increase the kubelet ``nodeStatusMaxImages`` setting.  The default value of 50 should either be increased to something large enough that it's implausible that that many images would fit into ephemeral storage, or set to ``-1`` to remove the cap entirely.  While disabling the cap could, in theory, make node status extremely large (which is the reason the cap exists in the first place), in practice it has never proven problematic in a Phalanx deployment.  Those deployments have had at most hundreds, rather than thousands or millions, of container images on any given node, so the size of the status document has always remained modest.

Should you go the route of choosing a larger positive value for ``nodeStatusMaxImages`` a reasonable rule of thumb is to pick a number one-third of the size of each node's ephemeral storage in gigabytes.  Thus if you had a terabyte of ephemeral storage, a ``nodeStatusMaxImages`` of ``350`` would be a good starting guess.  This value is also dependent on how broadly mixed your workload is, and how large the images for the other aspects of your workload are, which is why disabling the cap entirely is the initial recommendation.

Pruning cached images
=====================

If you cannot change the behavior of the Kubernetes node API, you may need to trim the node image cache so that the total number of images is under 50.
If you have direct administrative access to the Kubernetes node, you can do that with the following steps:

#. Download `purge <https://github.com/lsst-sqre/imagepurger/blob/main/node-script/purge>`__.

#. Run it on each node, using an account allowed to use the Docker socket (thus, probably in group ``docker``).
   You may want to run it with ``-x`` first to see what it's going to do.
   If you want output during the actual run, run it with ``-v``.

Unfortunately, this will only temporarily solve the problem, so you will either need to do this repeatedly or find a way to change the API configuration to return more cached images.
