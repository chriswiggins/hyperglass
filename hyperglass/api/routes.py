"""API Routes."""

# Standard Library
import json
import time
from datetime import datetime

# Third Party
from fastapi import Depends, HTTPException, BackgroundTasks
from starlette.requests import Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html

# Project
from hyperglass.log import log
from hyperglass.state import HyperglassState, use_state
from hyperglass.external import Webhook, bgptools
from hyperglass.api.tasks import process_headers
from hyperglass.constants import __version__
from hyperglass.exceptions import HyperglassError
from hyperglass.models.api import Query
from hyperglass.execution.main import execute

# Local
from .fake_output import fake_output


def get_state():
    """Get hyperglass state as a FastAPI dependency."""
    return use_state()


async def send_webhook(
    query_data: Query, request: Request, timestamp: datetime,
):
    """If webhooks are enabled, get request info and send a webhook."""
    state = use_state()
    try:
        if state.params.logging.http is not None:
            headers = await process_headers(headers=request.headers)

            if headers.get("x-real-ip") is not None:
                host = headers["x-real-ip"]
            elif headers.get("x-forwarded-for") is not None:
                host = headers["x-forwarded-for"]
            else:
                host = request.client.host

            network_info = await bgptools.network_info(host)

            async with Webhook(state.params.logging.http) as hook:

                await hook.send(
                    query={
                        **query_data.export_dict(pretty=True),
                        "headers": headers,
                        "source": host,
                        "network": network_info.get(host, {}),
                        "timestamp": timestamp,
                    }
                )
    except Exception as err:
        log.error("Error sending webhook to {}: {}", state.params.logging.http.provider, str(err))


async def query(
    query_data: Query,
    request: Request,
    background_tasks: BackgroundTasks,
    state: "HyperglassState" = Depends(get_state),
):
    """Ingest request data pass it to the backend application to perform the query."""

    timestamp = datetime.utcnow()
    background_tasks.add_task(send_webhook, query_data, request, timestamp)

    # Initialize cache
    cache = state.redis
    log.debug("Initialized cache {}", repr(cache))

    # Use hashed query_data string as key for for k/v cache store so
    # each command output value is unique.
    cache_key = f"hyperglass.query.{query_data.digest()}"

    log.info("Starting query execution for query {}", query_data.summary)

    cache_response = cache.get_dict(cache_key, "output")

    json_output = False

    if query_data.device.structured_output and query_data.query_type in (
        "bgp_route",
        "bgp_community",
        "bgp_aspath",
    ):
        json_output = True

    cached = False
    runtime = 65535
    if cache_response:
        log.debug("Query {} exists in cache", cache_key)

        # If a cached response exists, reset the expiration time.
        cache.expire(cache_key, seconds=state.params.cache.timeout)

        cached = True
        runtime = 0
        timestamp = cache.get_dict(cache_key, "timestamp")

    elif not cache_response:
        log.debug("No existing cache entry for query {}", cache_key)
        log.debug("Created new cache key {} entry for query {}", cache_key, query_data.summary)

        timestamp = query_data.timestamp

        starttime = time.time()

        if state.params.fake_output:
            # Return fake, static data for development purposes, if enabled.
            cache_output = await fake_output(json_output)
        else:
            # Pass request to execution module
            cache_output = await execute(query_data)

        endtime = time.time()
        elapsedtime = round(endtime - starttime, 4)
        log.debug("Query {} took {} seconds to run.", cache_key, elapsedtime)

        if cache_output is None:
            raise HyperglassError(message=state.params.messages.general, alert="danger")

        # Create a cache entry
        if json_output:
            raw_output = json.dumps(cache_output)
        else:
            raw_output = str(cache_output)
        cache.set_dict(cache_key, "output", raw_output)
        cache.set_dict(cache_key, "timestamp", timestamp)
        cache.expire(cache_key, seconds=state.params.cache.timeout)

        log.debug("Added cache entry for query: {}", cache_key)

        runtime = int(round(elapsedtime, 0))

    # If it does, return the cached entry
    cache_response = cache.get_dict(cache_key, "output")
    response_format = "text/plain"

    if json_output:
        response_format = "application/json"

    log.debug("Cache match for {}:\n{}", cache_key, cache_response)
    log.success("Completed query execution for query {}", query_data.summary)

    return {
        "output": cache_response,
        "id": cache_key,
        "cached": cached,
        "runtime": runtime,
        "timestamp": timestamp,
        "format": response_format,
        "random": query_data.random(),
        "level": "success",
        "keywords": [],
    }


async def docs(state: "HyperglassState" = Depends(get_state)):
    """Serve custom docs."""
    if state.params.docs.enable:
        docs_func_map = {"swagger": get_swagger_ui_html, "redoc": get_redoc_html}
        docs_func = docs_func_map[state.params.docs.mode]
        return docs_func(
            openapi_url=state.params.docs.openapi_url, title=state.params.site_title + " - API Docs"
        )
    else:
        raise HTTPException(detail="Not found", status_code=404)


async def router(id: str, state: "HyperglassState" = Depends(get_state)):
    """Get a device's API-facing attributes."""
    return state.devices[id].export_api()


async def routers(state: "HyperglassState" = Depends(get_state)):
    """Serve list of configured routers and attributes."""
    return state.devices.export_api()


async def queries(state: "HyperglassState" = Depends(get_state)):
    """Serve list of enabled query types."""
    return state.params.queries.list


async def info(state: "HyperglassState" = Depends(get_state)):
    """Serve general information about this instance of hyperglass."""
    return {
        "name": state.params.site_title,
        "organization": state.params.org_name,
        "primary_asn": int(state.params.primary_asn),
        "version": __version__,
    }


async def ui_props(state: "HyperglassState" = Depends(get_state)):
    """Serve UI configration."""
    return state.ui_params


endpoints = [query, docs, routers, info, ui_props]
