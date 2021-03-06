###############################################################################
# Define everything needed to build nightly Julia builds against LLVM SVN for Cxx.jl
###############################################################################

julia_cxx_builders = ["nightly_cxx32", "nightly_cxx64"]
cxx_nightly_scheduler = Nightly(name="Julia Cxx package", builderNames=julia_cxx_builders, hour=[0,12], branch="master", onlyIfChanged=True )
c['schedulers'].append(cxx_nightly_scheduler)

julia_cxx_factory = BuildFactory()
julia_cxx_factory.useProgress = True
julia_cxx_factory.addSteps([
    # Clone julia
    Git(
    	name="Julia checkout",
    	repourl=Property('repository', default='git://github.com/JuliaLang/julia.git'),
    	mode='incremental',
    	method='clean',
    	submodules=True,
    	clobberOnFailure=True,
    	progress=True
    ),
    # Fetch so that remote branches get updated as well.
    ShellCommand(
    	name="git fetch",
    	command=["git", "fetch"],
    	flunkOnFailure=False
    ),

    # Add our particular configuration to flags
    SetPropertyFromCommand(
        name="Add configuration to flags",
        command=["echo", Interpolate("%(prop:flags)s LLVM_VER=svn LLVM_ASSERTIONS=1 BUILD_LLVM_CLANG=1 BUILD_LLDB=1 USE_LLVM_SHLIB=1 LLDB_DISABLE_PYTHON=1")],
        property="flags"
    ),

    # make clean first, and nuke llvm
    ShellCommand(
    	name="make cleanall",
    	command=["/bin/bash", "-c", Interpolate("make %(prop:flags)s cleanall")]
    ),
    ShellCommand(
    	name="make distclean-llvm",
    	command=["/bin/bash", "-c", Interpolate("make %(prop:flags)s -C deps distclean-llvm")]
    ),

    # Make!
    ShellCommand(
        name="make binary-dist",
        command=["/bin/bash", "-c", Interpolate("make %(prop:flags)s binary-dist")],
        haltOnFailure = True
    ),

    # Upload the result!
    MasterShellCommand(
        name="mkdir julia_package",
        command=["mkdir", "-p", "/tmp/julia_package"]
    ),
    FileUpload(
        slavesrc=Interpolate("juliacxx-%(prop:shortcommit)s-Linux-%(prop:tar_arch)s.tar.gz"),
        masterdest=Interpolate("/tmp/julia_package/juliacxx-%(prop:shortcommit)s-Linux-%(prop:tar_arch)s.tar.gz")
    ),

    # Upload it to AWS and cleanup the master!
    MasterShellCommand(
        name="Upload to AWS",
        command=["/bin/bash", "-c", Interpolate("~/bin/aws put --fail --public julianightlies/bin/linux/%(prop:up_arch)s/%(prop:majmin)s/juliacxx-%(prop:version)s-%(prop:shortcommit)s-linux%(prop:bits)s.tar.gz /tmp/julia_package/juliacxx-%(prop:shortcommit)s-Linux-%(prop:tar_arch)s.tar.gz")],
        haltOnFailure=True
    ),
    MasterShellCommand(
        name="Upload to AWS (latest)",
        command=["/bin/bash", "-c", Interpolate("~/bin/aws put --fail --public julianightlies/bin/linux/%(prop:up_arch)s/juliacxx-latest-linux%(prop:bits)s.tar.gz /tmp/julia_package/julia-%(prop:shortcommit)s-Linux-%(prop:tar_arch)s.tar.gz")],
        doStepIf=is_nightly_build,
        haltOnFailure=True
    ),
    MasterShellCommand(
        name="Cleanup Master",
        command=["rm", "-f", Interpolate("/tmp/julia_package/juliacxx-%(prop:shortcommit)s-Linux-%(prop:tar_arch)s.tar.gz")]
    ),

    ShellCommand(
        name="Report success",
        command=["curl", "-L", "-H", "Content-type: application/json", "-d", Interpolate('{"target": "linux_cxx-%(prop:tar_arch)s", "url":"https://s3.amazonaws.com/julianightlies/bin/linux/%(prop:up_arch)s/%(prop:majmin)s/juliacxx-%(prop:version)s-%(prop:shortcommit)s-linux%(prop:bits)s.tar.gz", "version": "%(prop:shortcommit)s"}'), "https://status.julialang.org/put/nightly"],
        doStepIf=is_nightly_build
    ),
])


# Add linux tarball builders
c['builders'].append(BuilderConfig(
    name="nightly_cxx32",
    slavenames=["ubuntu12.04-x86"],
    category="Packaging",
    factory=julia_cxx_factory
))

c['builders'].append(BuilderConfig(
    name="nightly_cxx64",
    slavenames=["ubuntu12.04-x64"],
    category="Nightlies",
    factory=julia_cxx_factory
))
