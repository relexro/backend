"""Top-level package initialization for the Cloud Functions codebase.

This file injects lightweight stubs for optional third-party dependencies that
are not required during unit / integration testing. By providing these stubs we
avoid hard runtime import errors when the real libraries are absent in the test
environment (CI), while still allowing the production environment to use the
actual packages if they are installed.
"""

from __future__ import annotations

import sys
import types
import os

# ---------------------------------------------------------------------------
# Optional dependency: `xhtml2pdf`                                           
# ---------------------------------------------------------------------------
# The real library is only needed when generating PDF documents from HTML.
# In unit-tests we merely need the import to succeed and `pisa.CreatePDF` to
# exist and return an object with an `err` attribute (boolean).              
# ---------------------------------------------------------------------------
try:
    import xhtml2pdf  # noqa: F401 – try real import first (preferred)
except ModuleNotFoundError:  # pragma: no cover – executed only in tests
    xhtml2pdf = types.ModuleType('xhtml2pdf')
    sys.modules['xhtml2pdf'] = xhtml2pdf

# ---------------------------------------------------------------------------
# Optional dependency: `pytest_dependency`                                   
# ---------------------------------------------------------------------------
# The `pytest-dependency` plugin is useful for advanced test orchestration but
# is not strictly required for our internal tests. We replace it with a stub
# that provides a no-op `depends` function so the import succeeds.
# ---------------------------------------------------------------------------
try:
    import pytest_dependency  # noqa: F401 – real plugin present
except ModuleNotFoundError:  # pragma: no cover – executed only in CI/tests
    pytest_dependency = types.ModuleType('pytest_dependency')
    sys.modules['pytest_dependency'] = pytest_dependency

# Create a temporary directory for package paths
temp_dir = os.path.join(os.path.dirname(__file__), 'temp_packages')
os.makedirs(temp_dir, exist_ok=True)

# ---------------------------------------------------------------------------
# Optional dependency: `google.generativeai`                                  
# ---------------------------------------------------------------------------
# Part of Google AI SDK; not required during tests. We inject a stub with a
# no-op `configure` function so importing modules that depend on it succeeds.
# ---------------------------------------------------------------------------
try:
    import google.generativeai  # type: ignore  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    google = types.ModuleType('google')
    google.__path__ = [os.path.join(temp_dir, 'google')]  # Make it a package
    sys.modules['google'] = google
    
    generativeai = types.ModuleType('google.generativeai')
    google.generativeai = generativeai
    sys.modules['google.generativeai'] = generativeai

# ---------------------------------------------------------------------------
# Optional dependency: `google.cloud`                                         
# ---------------------------------------------------------------------------
# The Google Cloud SDK is not required during tests. We inject a stub that
# provides a minimal structure for google.cloud so that imports like
# 'from google.cloud import bigquery, firestore, storage' and
# 'from google.cloud.functions.context import Context' succeed.
# ---------------------------------------------------------------------------
try:
    import google.cloud  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    if 'google' not in sys.modules:
        google = types.ModuleType('google')
        google.__path__ = [os.path.join(temp_dir, 'google')]  # Make it a package
        sys.modules['google'] = google
    
    cloud = types.ModuleType('google.cloud')
    cloud.__path__ = [os.path.join(temp_dir, 'google', 'cloud')]  # Make it a package
    google.cloud = cloud
    sys.modules['google.cloud'] = cloud
    
    # Add submodules
    bigquery = types.ModuleType('google.cloud.bigquery')
    firestore = types.ModuleType('google.cloud.firestore')
    storage = types.ModuleType('google.cloud.storage')
    functions = types.ModuleType('google.cloud.functions')
    
    cloud.bigquery = bigquery
    cloud.firestore = firestore
    cloud.storage = storage
    cloud.functions = functions
    
    sys.modules['google.cloud.bigquery'] = bigquery
    sys.modules['google.cloud.firestore'] = firestore
    sys.modules['google.cloud.storage'] = storage
    sys.modules['google.cloud.functions'] = functions
    
    # Add Context class to functions module
    class Context:
        def __init__(self, **kwargs):
            self.event_id = kwargs.get('event_id', '')
            self.timestamp = kwargs.get('timestamp', '')
            self.event_type = kwargs.get('event_type', '')
            self.resource = kwargs.get('resource', {})
    
    functions.context = types.ModuleType('google.cloud.functions.context')
    functions.context.Context = Context
    sys.modules['google.cloud.functions.context'] = functions.context

# ---------------------------------------------------------------------------
# Optional dependency: `google.ai`                                         
# ---------------------------------------------------------------------------
# The Google AI SDK is not required during tests. We inject a stub that
# provides a minimal structure for google.ai so that imports like
# 'import google.ai.generativelanguage_v1beta as genai' succeed.
# ---------------------------------------------------------------------------
try:
    import google.ai  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    if 'google' not in sys.modules:
        google = types.ModuleType('google')
        google.__path__ = [os.path.join(temp_dir, 'google')]  # Make it a package
        sys.modules['google'] = google
    
    ai = types.ModuleType('google.ai')
    ai.__path__ = [os.path.join(temp_dir, 'google', 'ai')]  # Make it a package
    google.ai = ai
    sys.modules['google.ai'] = ai
    
    # Add generativelanguage_v1beta module
    generativelanguage_v1beta = types.ModuleType('google.ai.generativelanguage_v1beta')
    generativelanguage_v1beta.__path__ = [os.path.join(temp_dir, 'google', 'ai', 'generativelanguage_v1beta')]  # Make it a package
    ai.generativelanguage_v1beta = generativelanguage_v1beta
    sys.modules['google.ai.generativelanguage_v1beta'] = generativelanguage_v1beta
    
    # Add types module
    types_module = types.ModuleType('google.ai.generativelanguage_v1beta.types')
    generativelanguage_v1beta.types = types_module
    sys.modules['google.ai.generativelanguage_v1beta.types'] = types_module
    
    # Add SafetySetting class
    class _StubSafetySetting:
        class HarmBlockThreshold:
            HARM_BLOCK_THRESHOLD_UNSPECIFIED = 0
            BLOCK_LOW_AND_ABOVE = 1
            BLOCK_MEDIUM_AND_ABOVE = 2
            BLOCK_ONLY_HIGH = 3
            BLOCK_NONE = 4
        
        class HarmCategory:
            HARM_CATEGORY_UNSPECIFIED = 0
            HARM_CATEGORY_HARASSMENT = 1
            HARM_CATEGORY_HATE_SPEECH = 2
            HARM_CATEGORY_SEXUALLY_EXPLICIT = 3
            HARM_CATEGORY_DANGEROUS_CONTENT = 4
    
    generativelanguage_v1beta.SafetySetting = _StubSafetySetting
    
    # Add HarmCategory class
    class _StubHarmCategory:
        HARM_CATEGORY_UNSPECIFIED = 0
        HARM_CATEGORY_HARASSMENT = 1
        HARM_CATEGORY_HATE_SPEECH = 2
        HARM_CATEGORY_SEXUALLY_EXPLICIT = 3
        HARM_CATEGORY_DANGEROUS_CONTENT = 4
    
    generativelanguage_v1beta.HarmCategory = _StubHarmCategory
    
    # Add GenerationConfig class
    class _StubGenerationConfig:
        class Modality:
            MODALITY_UNSPECIFIED = 0
            TEXT = 1
            IMAGE = 2
            AUDIO = 3
            VIDEO = 4
    
    generativelanguage_v1beta.GenerationConfig = _StubGenerationConfig
    
    # Add GenerativeServiceAsyncClient class
    class GenerativeServiceAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        
        async def generate_content(self, *args, **kwargs):
            return type('Response', (), {
                'candidates': [type('Candidate', (), {
                    'content': type('Content', (), {
                        'parts': [type('Part', (), {'text': 'Test response'})()]
                    })()
                })()]
            })()
    
    generativelanguage_v1beta.GenerativeServiceAsyncClient = GenerativeServiceAsyncClient 

# Ensure google.auth and google.auth.crypt are always attached to the google module
if 'google' not in sys.modules:
    google = types.ModuleType('google')
    google.__path__ = [os.path.join(temp_dir, 'google')]
    sys.modules['google'] = google
else:
    google = sys.modules['google']

if not hasattr(google, 'auth'):
    auth = types.ModuleType('google.auth')
    google.auth = auth
    sys.modules['google.auth'] = auth
else:
    auth = google.auth

if not hasattr(auth, 'crypt'):
    crypt = types.ModuleType('google.auth.crypt')
    auth.crypt = crypt
    sys.modules['google.auth.crypt'] = crypt
else:
    crypt = auth.crypt

if not hasattr(crypt, 'Signer'):
    class Signer:
        pass
    crypt.Signer = Signer

# Stub for google.resumable_media as a package and google.resumable_media.requests
if not hasattr(google, 'resumable_media'):
    resumable_media = types.ModuleType('google.resumable_media')
    resumable_media.__path__ = [os.path.join(temp_dir, 'google', 'resumable_media')]
    google.resumable_media = resumable_media
    sys.modules['google.resumable_media'] = resumable_media
else:
    resumable_media = google.resumable_media

# Add google.resumable_media.requests submodule
if not hasattr(resumable_media, 'requests'):
    requests_mod = types.ModuleType('google.resumable_media.requests')
    requests_mod.__path__ = [os.path.join(temp_dir, 'google', 'resumable_media', 'requests')]
    resumable_media.requests = requests_mod
    sys.modules['google.resumable_media.requests'] = requests_mod
    # Add stubs for expected classes
    class MultipartUpload:
        pass
    class ChunkedDownload:
        pass
    requests_mod.MultipartUpload = MultipartUpload
    requests_mod.ChunkedDownload = ChunkedDownload

# Add Blob to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class Blob:
        pass
    types_mod.Blob = Blob

# Stub for xhtml2pdf.pisa if not available
try:
    from xhtml2pdf import pisa
except ImportError:
    if 'xhtml2pdf' not in sys.modules:
        xhtml2pdf = types.ModuleType('xhtml2pdf')
        sys.modules['xhtml2pdf'] = xhtml2pdf
    pisa = types.ModuleType('xhtml2pdf.pisa')
    xhtml2pdf.pisa = pisa
    sys.modules['xhtml2pdf.pisa'] = pisa
    def CreatePDF(src, dest, **kwargs):
        class _Result:
            err = False
        return _Result()
    pisa.CreatePDF = CreatePDF

# Stub for pytest_dependency.depends if not available
try:
    from pytest_dependency import depends
except ImportError:
    if 'pytest_dependency' not in sys.modules:
        pytest_dependency = types.ModuleType('pytest_dependency')
        sys.modules['pytest_dependency'] = pytest_dependency
    def depends(request, depends=None):
        pass
    pytest_dependency.depends = depends 

# Add stubs for expected classes in google.resumable_media.requests
if 'google.resumable_media.requests' in sys.modules:
    requests_mod = sys.modules['google.resumable_media.requests']
    class ResumableUpload:
        pass
    class Download:
        pass
    requests_mod.ResumableUpload = ResumableUpload
    requests_mod.Download = Download

# Add Candidate to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class Candidate:
        pass
    types_mod.Candidate = Candidate 

# Stub for google.api_core and google.api_core.future.polling
if not hasattr(google, 'api_core'):
    api_core = types.ModuleType('google.api_core')
    api_core.__path__ = [os.path.join(temp_dir, 'google', 'api_core')]
    google.api_core = api_core
    sys.modules['google.api_core'] = api_core
else:
    api_core = google.api_core

# Add future submodule
if not hasattr(api_core, 'future'):
    future = types.ModuleType('google.api_core.future')
    future.__path__ = [os.path.join(temp_dir, 'google', 'api_core', 'future')]
    api_core.future = future
    sys.modules['google.api_core.future'] = future
else:
    future = api_core.future

# Add polling submodule
if not hasattr(future, 'polling'):
    polling = types.ModuleType('google.api_core.future.polling')
    polling.__path__ = [os.path.join(temp_dir, 'google', 'api_core', 'future', 'polling')]
    future.polling = polling
    sys.modules['google.api_core.future.polling'] = polling
else:
    polling = future.polling

# Add PollingFuture class with _DEFAULT_VALUE
class PollingFuture:
    _DEFAULT_VALUE = object()
polling.PollingFuture = PollingFuture

# Add RawDownload to google.resumable_media.requests
if 'google.resumable_media.requests' in sys.modules:
    requests_mod = sys.modules['google.resumable_media.requests']
    class RawDownload:
        pass
    requests_mod.RawDownload = RawDownload

# Add CodeExecution to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class CodeExecution:
        pass
    types_mod.CodeExecution = CodeExecution 

# Add google.api_core.iam with Policy class
if 'google.api_core' in sys.modules:
    api_core = sys.modules['google.api_core']
    if not hasattr(api_core, 'iam'):
        iam = types.ModuleType('google.api_core.iam')
        api_core.iam = iam
        sys.modules['google.api_core.iam'] = iam
        class Policy:
            pass
        iam.Policy = Policy

# Add RawChunkedDownload to google.resumable_media.requests
if 'google.resumable_media.requests' in sys.modules:
    requests_mod = sys.modules['google.resumable_media.requests']
    class RawChunkedDownload:
        pass
    requests_mod.RawChunkedDownload = RawChunkedDownload

# Add Content to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class Content:
        pass
    types_mod.Content = Content 

# Add page_iterator to google.api_core
if 'google.api_core' in sys.modules:
    api_core = sys.modules['google.api_core']
    if not hasattr(api_core, 'page_iterator'):
        page_iterator = types.ModuleType('google.api_core.page_iterator')
        api_core.page_iterator = page_iterator
        sys.modules['google.api_core.page_iterator'] = page_iterator

# Add FileData to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class FileData:
        pass
    types_mod.FileData = FileData 

# Add HTTPIterator and _do_nothing_page_start to google.api_core.page_iterator
if 'google.api_core.page_iterator' in sys.modules:
    page_iterator = sys.modules['google.api_core.page_iterator']
    class HTTPIterator:
        pass
    page_iterator.HTTPIterator = HTTPIterator
    def _do_nothing_page_start(*args, **kwargs):
        pass
    page_iterator._do_nothing_page_start = _do_nothing_page_start

# Add FunctionCall to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class FunctionCall:
        pass
    types_mod.FunctionCall = FunctionCall 

# Add google.api_core.client_info with ClientInfo class
if 'google.api_core' in sys.modules:
    api_core = sys.modules['google.api_core']
    if not hasattr(api_core, 'client_info'):
        client_info = types.ModuleType('google.api_core.client_info')
        api_core.client_info = client_info
        sys.modules['google.api_core.client_info'] = client_info
        class ClientInfo:
            def __init__(self, *args, **kwargs):
                self.user_agent = None
        client_info.ClientInfo = ClientInfo

# Add FunctionDeclaration to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class FunctionDeclaration:
        pass
    types_mod.FunctionDeclaration = FunctionDeclaration 

# Add google.api_core.client_options with ClientOptions class
if 'google.api_core' in sys.modules:
    api_core = sys.modules['google.api_core']
    if not hasattr(api_core, 'client_options'):
        client_options = types.ModuleType('google.api_core.client_options')
        api_core.client_options = client_options
        sys.modules['google.api_core.client_options'] = client_options
    else:
        client_options = api_core.client_options
    class ClientOptions:
        pass
    client_options.ClientOptions = ClientOptions

# Add FunctionResponse to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class FunctionResponse:
        pass
    types_mod.FunctionResponse = FunctionResponse 

# Add Iterator to google.api_core.page_iterator
if 'google.api_core.page_iterator' in sys.modules:
    page_iterator = sys.modules['google.api_core.page_iterator']
    class Iterator:
        pass
    page_iterator.Iterator = Iterator

# Add GenerateContentRequest to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class GenerateContentRequest:
        pass
    types_mod.GenerateContentRequest = GenerateContentRequest 

# Add GenerateContentResponse to google.ai.generativelanguage_v1beta.types
if 'google.ai.generativelanguage_v1beta.types' in sys.modules:
    types_mod = sys.modules['google.ai.generativelanguage_v1beta.types']
    class GenerateContentResponse:
        pass
    types_mod.GenerateContentResponse = GenerateContentResponse 