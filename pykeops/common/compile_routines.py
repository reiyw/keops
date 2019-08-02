import subprocess
import sys

from pykeops import bin_folder, script_folder, verbose, build_type
from pykeops.common.parse_type import check_aliases_list
from pykeops.common.utils import c_type

# cmake can't find a python executable installed with pyenv 💩
PYTHON_EXECUTABLE = sys.executable


def find_cmake_executable():
    paths = subprocess.run(['which', '-a', 'cmake'], stdout=subprocess.PIPE).stdout.decode('utf-8').split()
    for path in paths:
        if not 'pyenv' in path:
            return path
    return 'cmake'


# pyenv hide a executable if it's installed in at least one environment 💩
CMAKE = find_cmake_executable()


def run_and_display(args, build_folder, msg=''):
    """
    This function run the command stored in args and display the output if needed
    :param args: list
    :param msg: str
    :return: None
    """
    try:
        proc = subprocess.run(args, cwd=build_folder, stdout=subprocess.PIPE, check=True)
        if verbose:
            print(proc.stdout.decode('utf-8'))

    except subprocess.CalledProcessError as e:
        print('\n--------------------- ' + msg + ' DEBUG -----------------')
        print(e)
        print(e.stdout.decode('utf-8'))
        print('--------------------- ----------- -----------------')


def compile_generic_routine(formula, aliases, dllname, dtype, lang, optional_flags, build_folder=bin_folder):
    aliases = check_aliases_list(aliases)

    def process_alias(alias):
        if alias.find("=") == -1:
            return ''  # because in this case it is not really an alias, the variable is just named
        else:
            return 'auto ' + str(alias) + '; '

    def process_disp_alias(alias):
        return str(alias) + '; '

    alias_string = ''.join([process_alias(alias) for alias in aliases])
    alias_disp_string = ''.join([process_disp_alias(alias) for alias in aliases])

    print(
        'Compiling ' + dllname + ' in ' + build_folder + ':\n' + '       formula: ' + formula + '\n       aliases: ' + alias_disp_string + '\n       dtype  : ' + dtype + '\n... ',
        end='', flush=True)
    
    print('💩')

    command_line = [CMAKE, script_folder,
                     '-DCMAKE_BUILD_TYPE=' + build_type,
                     '-DFORMULA_OBJ=' + formula,
                     '-DVAR_ALIASES=' + alias_string,
                     '-Dshared_obj_name=' + dllname,
                     '-D__TYPE__=' + c_type[dtype],
                     '-DPYTHON_LANG=' + lang,
                     '-DPYTHON_EXECUTABLE=' + PYTHON_EXECUTABLE,
                     ] + optional_flags
    run_and_display(command_line + ['-DcommandLine=' + ' '.join(command_line)],
                    build_folder,
                    msg='CMAKE')

    run_and_display([CMAKE, '--build', '.', '--target', dllname, '--', 'VERBOSE=1'], build_folder, msg='MAKE')
    
    print('Done.')


def compile_specific_conv_routine(dllname, dtype, build_folder=bin_folder):
    print('Compiling ' + dllname + ' using ' + dtype + '... ', end='', flush=True)
    run_and_display([CMAKE, script_folder,
                     '-DCMAKE_BUILD_TYPE=' + build_type,
                     '-Ushared_obj_name',
                     '-D__TYPE__=' + c_type[dtype],
                     ],
                    build_folder,
                    msg='CMAKE')
    run_and_display([CMAKE, '--build', '.', '--target', dllname, '--', 'VERBOSE=1'], build_folder, msg='MAKE')
    print('Done.')


def compile_specific_fshape_scp_routine(dllname, kernel_geom, kernel_sig, kernel_sphere, dtype,
                                        build_folder=bin_folder):
    print('Compiling ' + dllname + ' using ' + dtype + '... ', end='', flush=True)
    run_and_display([CMAKE, script_folder,
                     '-DCMAKE_BUILD_TYPE=' + build_type,
                     '-Ushared_obj_name',
                     '-DKERNEL_GEOM=' + kernel_geom,
                     '-DKERNEL_SIG=' + kernel_sig,
                     '-DKERNEL_SPHERE=' + kernel_sphere,
                     '-D__TYPE__=' + c_type[dtype],
                     ],
                    build_folder,
                    msg='CMAKE')
    run_and_display([CMAKE, '--build', '.', '--target', dllname, '--', 'VERBOSE=1'], build_folder, msg='MAKE')
    print('Done.')
