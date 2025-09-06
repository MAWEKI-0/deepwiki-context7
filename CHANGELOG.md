# Changelog

## Summary

This update modernizes the application's core AI/LLM libraries, including `llama-index` and `langchain`, to their latest major versions. The `requirements.txt` file has been updated with a compatible set of modern libraries, and the application code has been refactored to align with the new APIs and package structures.

All unit tests are passing after the refactoring. However, the end-to-end tests could not be run due to a persistent database connectivity issue.

## Library Upgrades

The following libraries were upgraded:

- `llama-index` was upgraded to a modular structure, with `llama-index-core` as the main component.
- `langchain` was upgraded to a modular structure, with `langchain-core` and `langchain-community` as key components.
- `google-generativeai` was renamed to `google-genai`.
- `pydantic` was upgraded to v2.

The final set of installed libraries can be found by running `pip freeze`.

## Code Refactoring

The following changes were made to the source code to support the library upgrades:

- **`src/enrichment_pipeline.py`**:
  - Updated the import for `google.generativeai` to `google.genai`.
  - Replaced `PydanticOutputParser` with `JsonOutputParser` for more robust JSON parsing.
  - Updated the prompt templates to work with `JsonOutputParser`.
  - Modified the enrichment functions to parse the JSON output into Pydantic models.
  - Corrected the import path for `GoogleGenerativeAIEmbeddings`.

- **`src/query_engine.py`**:
  - Updated all `llama_index` imports to their new locations in the modular package structure.
  - Corrected the import path for `GoogleGenerativeAIEmbeddings`.
  - Added `llama-index-vector-stores-supabase` to the dependencies.

- **`src/dependencies.py`**:
  - Removed the `LangChainLLM` wrapper from the Gemini client creation functions to return `ChatGoogleGenerativeAI` instances directly, resolving a type mismatch.
  - Updated the `google.generativeai` import to `google.genai`.

- **`src/tasks.py` and `src/celery_app.py`**:
  - Resolved a circular import by moving the `BaseTaskWithClients` class to a new file, `src/celery_base.py`.
  - Updated the type hints in `src/tasks.py` to match the changes in `src/dependencies.py`.

- **`tests/test_main.py`**:
  - Removed unused imports that were causing test collection to fail.
  - Fixed a failing test to correctly handle exceptions caught by the FastAPI global exception handler.

## Unresolved Issues

### Database Connectivity Error

The end-to-end test suite could not be run due to a persistent database connectivity issue. The following error was encountered when trying to apply the database migrations:

`psycopg2.OperationalError`

**Diagnosis:**

- The error indicates that the application is unable to establish a connection with the Supabase PostgreSQL database.
- The `SUPABASE_CONNECTION_STRING` is correctly defined in the `.env` file.
- An attempt to `ping` the database host (`db.rgdklrmrtftgsbmydsod.supabase.co`) failed with an "Address family for hostname not supported" error, which strongly suggests a network issue between the execution environment and the database.

**Resolution Options Presented to the User:**

1.  **Check Network Access:** Verify that the sandbox environment has network access to the Supabase database host and port.
2.  **Verify Supabase Status:** Check the status of the Supabase project in the Supabase dashboard.
3.  **Alternative Database:** Switch to a different database that is accessible from the environment.
4.  **Mock the Database:** Modify the end-to-end tests to use a mocked database.
5.  **Manual Migration:** Apply the database migrations manually.

The user opted not to pursue these options at this time and requested that the work be submitted with this documentation. As a result, the end-to-end tests have not been run, and the application's full functionality has not been verified.
