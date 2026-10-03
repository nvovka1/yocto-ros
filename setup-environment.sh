# Prepare a BitBake shell for this repository.
# Usage (from the repository root, in bash):  source ./setup-environment.sh [build-directory]

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "This script must be sourced: source ./setup-environment.sh" >&2
    exit 1
fi

YOCTO_ROS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "${YOCTO_ROS_ROOT}/layers/poky/oe-init-build-env" ]; then
    echo "layers/poky is missing. Run: git submodule update --init" >&2
    return 1
fi

# TEMPLATECONF is only used when build/conf does not exist yet (first run).
export TEMPLATECONF="${YOCTO_ROS_ROOT}/meta-rpi-base/conf/templates/default"
. "${YOCTO_ROS_ROOT}/layers/poky/oe-init-build-env" "${YOCTO_ROS_ROOT}/${1:-build}"
