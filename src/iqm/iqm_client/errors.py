# Copyright 2024 IQM client developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""
This module contains error classes required by IQMClient.
"""


class ClientAuthenticationError(RuntimeError):
    """Something went wrong with user authentication."""


class ClientConfigurationError(RuntimeError):
    """Wrong configuration provided."""


class CircuitValidationError(RuntimeError):
    """Circuit validation failed."""


class CircuitExecutionError(RuntimeError):
    """Something went wrong on the server."""


class APITimeoutError(CircuitExecutionError):
    """Exception for when executing a job on the server takes too long."""


class JobAbortionError(RuntimeError):
    """Job abortion failed."""
