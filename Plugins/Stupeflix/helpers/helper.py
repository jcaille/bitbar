# -*- coding: utf-8 -*-

import codecs
import sys
from bundle import conf, utils
from bundle.build.states import (BuildStatesCache, get_build_states_cache_path, get_module_state)
from bundle.build.targets import get_xcompile_fingerprint
from bundle.build.platforms import _call_platform_fun as call_platform_fun
import os
from stupeflix.utils.commands import cd
import sh

UTF8Writer = codecs.getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)

EDITOR_COMMAND = "sublime"

def get_modules(platform = None, has_repo = None):
    module_conf = conf.defaults['bundle.build_modules']

    if platform :
        module_conf = {key : module_conf[key] for key in module_conf.keys() if platform.lower() in module_conf[key].get("targets", [])}
    if has_repo is not None :
        if has_repo :
            module_conf = {key : module_conf[key] for key in module_conf.keys() if "repos" in module_conf[key]}
        else :
            module_conf = {key : module_conf[key] for key in module_conf.keys() if "repos" not in module_conf[key]}
    return module_conf


def repos_status(repo_name):
    ''' Checks the status of a repo'''
    repos_base_dir = conf.get("bundle.repos_dir")
    repo_dir = os.path.join(repos_base_dir, repo_name)

    git_string = u""
    branch_string = u""

    if not os.path.exists(repo_dir):
        git_string = "❌"
    else :
        with cd(repo_dir):

            dirty = utils.git_is_dirty()
            branch = sh.git('rev-parse', '--abbrev-ref', 'HEAD').strip()
            freshness = utils.get_git_freshness(fetch = True)

            branch_string += u"(%s) " % (branch)

            if freshness == 0 :
                git_string += u"✅"
            elif freshness == 1 :
                git_string += u"⬇️"
            elif freshness == 2 :
                git_string += u"⬆️"
            elif freshness == 4 :
                git_string += u"↕️"
            elif freshness == 8 :
                git_string += u"❓"

            if dirty :
                git_string += u"🌀"
            else :
                git_string += u"⚪️"
    return git_string, branch_string

def module_status(module, platform = "ios"):
    ''' Checks the status of a module (by name) and returns a string'''
    # BUILD_STATE
    expected = None
    arch = None
    if platform == "ios" :
        arch = "arm64"
    elif platform == "android":
        arch = "armeabi-v7a"

    fingerprint = get_xcompile_fingerprint(platform, arch)
    build_states_path = get_build_states_cache_path(platform, arch)
    build_states = BuildStatesCache(build_states_path)
    expected = build_states.get(module)
    current = get_module_state(module, build_states, fingerprint, hash_result=True)
    build_states[module] = current
    if expected is None :
        return "unknown"
    elif expected != current :
        return "out_of_date"
    else :
        return "up_to_date"
    return "unknown"

def emoji_from_string(s):
    if s == "up_to_date":
        return u"✅"
    elif s == "out_of_date" :
        return u"🔨"
    return u"❌"

def print_platform_status(platform = "ios"):
    module_count = 0
    built_module_count = 0

    # Get the status of all modules
    git_modules = get_modules(platform = platform, has_repo = True).keys() ; git_modules.sort()
    git_modules_status = [module_status(m) for m in git_modules]
    module_count += len(git_modules_status)
    built_module_count += sum([s == "up_to_date" for s in git_modules_status])

    external_modules = get_modules(platform = platform, has_repo = False).keys() ; external_modules.sort()
    external_modules_status = [module_status(m) for m in external_modules]
    module_count += len(external_modules_status)
    built_module_count += sum([s == "up_to_date" for s in external_modules_status])

    global_status_string = ""
    if module_count == built_module_count :
        global_status_string = u"☀️"
    elif built_module_count > module_count / 2 :
        global_status_string = u"⛅️"
    else :
        global_status_string = u"☁️"


    print u"[%s %s] | refresh=true " % (platform, global_status_string)
    print "---"
    print "Build all | bash='senv ; sx build --xcompile %s all'" % (platform)
    print "---"

    for (m, s) in zip(git_modules, git_modules_status):
        s = emoji_from_string(s)
        print "%s %s | bash='senv ; sx build --xcompile %s %s --no-deps --rebuild'" % (s, m, platform, m)

    print "---"

    for (m, s) in zip(external_modules, external_modules_status):
        s = emoji_from_string(s)
        print "%s %s | bash='senv ; sx build --xcompile %s %s --no-deps --rebuild'" % (s, m, platform, m)

def print_repos_status(platform = None):
    git_modules = get_modules(platform = platform, has_repo = True)
    repos = list(set( [git_modules[k]["repos"] for k in git_modules.keys()] ))
    repos.sort()
    repos = ["bundle"] + repos

    print "[SX Git] | refresh=true"
    print "---"
    print "sx repos pull | bash='senv;sx repos pull'"
    print "sx repos clone | bash='senv;sx repos clone'"
    print "sx self_update | bash='senv;sx self_update'"
    print "---"
    repos_base_dir = conf.defaults.get("bundle.repos_dir")
    if repos_base_dir is None :
        repos_base_dir = "~/devel"
    for r in repos :
        git_string, branch_string = repos_status(r)
        repo_dir = os.path.join(repos_base_dir, r)
        print "%s %s %s | bash='%s %s;exit'" % (git_string, r, branch_string, EDITOR_COMMAND, repo_dir)


def print_status(module, is_module = True, build = True, custom_command = None):
    state_string = u"❓"
    git_string = u""
    branch_string = u""
    command_string = u""

    if is_module :
        state_string = module_status(module)
        repos = MODULES_DICT[module].get("repos", None)
        if repos :
            git_string, branch_string = repos_status(repos)
    else :
        git_string, branch_string = repos_status(module)

    res = " ".join([state_string, git_string ,module, branch_string])

    if build :
        build_script = "/Users/Jean/Documents/doBuild.sh"
        build_command = "| bash=%s param1=%s terminal=true" % (build_script, module)
        res += build_command
    elif custom_command :
        res += " | " + custom_command

    print res

if __name__ == '__main__':
    print_repos_status("ios")
