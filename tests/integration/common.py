import json
import os
import subprocess
import uuid

from contextlib import contextmanager

import pytest


def exec_cmd(cmd, env=None, stdin=None, timeout=None):
    """Execute CLI command

    :param cmd: Program and arguments
    :type cmd: [str]
    :param env: Environment variables
    :type env: dict | None
    :param stdin: File to use for stdin
    :type stdin: file
    :param timeout: The timeout for the process to terminate.
    :type timeout: int
    :raises: subprocess.TimeoutExpired when the timeout is reached
             before the process finished.
    :returns: A tuple with the returncode, stdout and stderr
    :rtype: (int, bytes, bytes)
    """

    print('CMD: {!r}'.format(cmd))

    process = subprocess.Popen(
        cmd,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env)

    try:
        streams = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # The child process is not killed if the timeout expires, so in order
        # to cleanup properly a well-behaved application should kill the child
        # process and finish communication.
        # https://docs.python.org/3.5/library/subprocess.html#subprocess.Popen.communicate
        process.kill()
        stdout, stderr = process.communicate()
        print(f"STDOUT: {stdout.decode('utf-8')}")
        print(f"STDERR: {stderr.decode('utf-8')}")
        raise

    # This is needed to get rid of '\r' from Windows's lines endings.
    stdout, stderr = [stream.replace(b'\r', b'').decode('utf-8') for stream in streams]

    # We should always print the stdout and stderr
    print(f'STDOUT: {stdout}')
    print(f'STDERR: {stderr}')

    return (process.returncode, stdout, stderr)


@pytest.fixture()
def default_cluster():
    cluster = _setup_cluster()

    yield cluster

    code, _, _ = exec_cmd(['dcos', 'cluster', 'remove', cluster['cluster_id']])
    assert code == 0


@contextmanager
def setup_cluster(**kwargs):
    try:
        cluster = _setup_cluster(**kwargs)
        yield cluster
    finally:
        code, _, _ = exec_cmd(['dcos', 'cluster', 'remove', cluster['cluster_id']])
        assert code == 0


def _setup_cluster(name='DEFAULT', scheme='https', insecure=True, env={}):
    env = {**os.environ.copy(), **env}
    cluster = {
        'variant': os.environ.get(f'DCOS_TEST_{name}_CLUSTER_VARIANT'),
        'username': os.environ.get(f'DCOS_TEST_{name}_CLUSTER_USERNAME'),
        'password': os.environ.get(f'DCOS_TEST_{name}_CLUSTER_PASSWORD'),
        'name': f'test_cluster_{str(uuid.uuid4())}',
    }


    cmd = f"dcos cluster setup --name={cluster['name']} --username={cluster['username']} --password={cluster['password']} {scheme}://{os.environ.get(f'DCOS_TEST_{name}_CLUSTER_HOST')}"


    if scheme == 'https':
        cmd += ' --no-check'

    if insecure:
        cmd += ' --insecure'

    code, _, _ = exec_cmd(cmd.split(' '), env=env)
    assert code == 0

    code, out, _ = exec_cmd(['dcos', 'cluster', 'list', '--json', '--attached'])
    clusters = json.loads(out)
    assert len(clusters) == 1
    assert clusters[0]['name'] == cluster['name']

    cluster['dcos_url'] = clusters[0]['url']
    cluster['version'] = clusters[0]['version']
    cluster['cluster_id'] = clusters[0]['cluster_id']

    code, out, _ = exec_cmd(['dcos', 'config', 'show', 'core.dcos_acs_token'])
    assert code == 0
    cluster['acs_token'] = out.rstrip()

    return cluster
