"""Wrapper around executing external commands."""

from __future__ import annotations

import subprocess
from datetime import timedelta
from pathlib import Path

from ..exceptions import CommandFailedError, CommandTimedOutError

__all__ = ["Command"]


class Command:
    """Wrapper around executing external commands.

    This class provides some generic wrappers around subprocess that are
    helpful for executing external commands, checking their status, and
    optionally capturing their output in a consistent way. It expects commands
    to take the form of a subcommand followed by arguments. It is intended for
    use by storage classes that perform operations via external commands.

    Parameters
    ----------
    command
        Base command. If this is not a full path, the command will be found on
        the user's PATH.
    """

    def __init__(self, command: str) -> None:
        self._command = command

    def capture(
        self, *args: str, cwd: Path | None = None
    ) -> subprocess.CompletedProcess:
        """Run the command, checking for errors and capturing the output.

        This method should only be called by subclasses, which should provide
        a higher-level interface used by the rest of the program.

        Parameters
        ----------
        *args
            Arguments for the command.
        cwd
            If provided, change working directories to this path before
            running the command.

        Returns
        -------
        subprocess.CompletedProcess
            Results of the process, containing the standard output and
            standard error streams.

        Raises
        ------
        CommandFailedError
            Raised if the command failed.
        subprocess.SubprocessError
            Raised if the command could not be executed at all.
        """
        try:
            result = subprocess.run(
                [self._command, *args],
                capture_output=True,
                check=True,
                cwd=cwd,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise CommandFailedError(self._command, args, e) from e
        return result

    def run(
        self,
        *args: str,
        cwd: Path | None = None,
        ignore_fail: bool = False,
        quiet: bool = False,
        stdin: str | None = None,
        timeout: timedelta | None = None,
    ) -> None:
        """Run the command with the provided arguments.

        Standard output and standard error are not redirected and will go to
        the standard output and error of the caller. This method should only
        be called by subclasses, which should provide a higher-level interface
        used by the rest of the program.

        Parameters
        ----------
        *args
            Arguments to the command.
        cwd
            If provided, change working directories to this path before
            running the command.
        ignore_fail
            If `True`, do not raise an exception on failure.
        stdin
            Input for the command.
        quiet
            If `True`, discard standard output. Standard error is still
            displayed on the process standard error stream.
        timeout
            If given, the command will be terminated and a
            `~phalanx.exceptions.CommandTimedOutError` will be raised if
            execution time exceeds this timeout.

        Raises
        ------
        CommandFailedError
            Raised if the command failed and ``ignore_fail`` was not set to
            `True`.
        CommandTimedOutError
            Raised if ``timeout`` was given and the command took longer than
            that to complete.
        subprocess.SubprocessError
            Raised if the command could not be executed at all.
        """
        cmdline = [self._command, *args]
        stdin_bytes = stdin.encode() if stdin is not None else None
        stdout = subprocess.DEVNULL if quiet else None
        check = not ignore_fail
        try:
            subprocess.run(
                cmdline, check=check, cwd=cwd, input=stdin_bytes, stdout=stdout
            )
        except subprocess.CalledProcessError as e:
            raise CommandFailedError(self._command, args, e) from e
        except subprocess.TimeoutExpired as e:
            raise CommandTimedOutError(self._command, args, e) from e
