from eventor.schemas import (
    Event,
    EventRace,
    Organisation,
    OrganisationList,
    ClassificationID,
    EventList,
    Person,
    PersonList,
    ResultList,
    ResultListList,
)
from enum import StrEnum
from typing import Any
import requests
from requests import Response
from typing import Iterator
from bs4 import BeautifulSoup
import parsy
import logging


class Endpoint(StrEnum):
    """Different API endpoints"""

    EVENT = "event"
    EVENTS = "events"
    RESULTS = "results/event"
    ORGANISATIONS = "organisations"
    PERSONS = "persons/organisations/"
    PERSON_RESULTS = "results/person"
    TOKEN_ORGANIZATION = "organisation/apiKey"


class EventorAPI:
    """A Python wrapper around the Eventor API."""

    def __init__(self, api_token: str) -> None:
        """Initialize the connection to the API.

        Args:
            api_token: The token to use for validation.
        """
        self.base_url = "https://eventor.orientering.se/api"
        self.api_token = api_token

    def _make_call(
        self,
        endpoint: Endpoint,
        params: dict[str, Any],
        headers: dict[str, Any],
        extra_path: str | None = None,
    ) -> Response:
        """Generic function for calling different enpoints of the API.

        Args:
            endpoint: The endpoint to call.
            params: Parameters to call the endpoint with.
            headers: Headers added to the request.
            extra_path: If a subpath to the endpoint should be used.
                Defaults to None.

        Returns:
            Response: A response from the API.
        """
        url = f"{self.base_url}/{endpoint}"
        if extra_path:
            url += f"/{extra_path}"
        resp = requests.get(url, params, headers=headers)
        logging.debug(f"GET {url} {params=} {headers=}")
        return resp

    def get_event(self, event_id: int) -> Event:
        """Get all information about a given event.

        Args:
            event_id: The ID of the event

        Returns:
            Event: A Event response
        """
        params: dict[str, Any] = {}
        headers = {
            "ApiKey": self.api_token,
        }
        response = self._make_call(
            Endpoint.EVENT, params, headers, extra_path=f"{event_id}"
        )
        return Event.from_xml(response.content)

    def get_all_organizations(self) -> Iterator[Organisation]:
        """Call the api and get an iterator over all organizations.

        Yields:
            Iterator[Organisation]: Iterator over all organisations.
        """

        params: dict[str, Any] = {}
        headers = {
            "ApiKey": self.api_token,
        }
        response = self._make_call(Endpoint.ORGANISATIONS, params, headers)
        oranisation_list = OrganisationList.from_xml(response.content)
        yield from oranisation_list.organisations

    def get_events(
        self,
        start_date: str,
        end_date: str,
        eventIds: list[int] | None = None,
        organisationIds: list[int] | None = None,
        classificationIds: list[ClassificationID] | None = None,
    ) -> Iterator[Event]:
        """Call the API and get an Iterator over all events within a range.

        Args:
            start_date: Start date as a string, i.e. 2010-01-01
            end_date:  Start date as a string, i.e. 2011-01-01
            eventIds: Only return events that are in the given list.
                Defaults to None.
            organisationIds: Only return events hosted by these organizations.
                Defaults to None.
            classificationIds: Only return events with these classification.
                Defaults to None.

        Yields:
            Iterator[Event]: Iterator over events matching provided criterias.
        """
        params: dict[str, Any] = {"fromDate": start_date, "toDate": end_date}

        if eventIds:
            params["eventIds"] = eventIds
        if organisationIds:
            params["organisationIds"] = ",".join(
                str(ids) for ids in organisationIds
            )
        if classificationIds:
            params["classificationIds"] = ",".join(
                str(int(cl)) for cl in classificationIds
            )

        headers = {
            "ApiKey": self.api_token,
        }
        resp = self._make_call(Endpoint.EVENTS, params, headers)
        yield from EventList.from_xml(resp.content).events

    def get_event_results(
        self, event_id: int, include_split_times: bool = False
    ) -> ResultList:
        """Get the result for a provided event.

        Args:
            event_id: ID of the event to get results for.
            include_split_times: Include split times in the result.
                Defaults to False.

        Returns:
            ResultList: The result as a ResultList.
        """
        params: dict[str, Any] = {"eventId": event_id}
        headers = {
            "ApiKey": self.api_token,
        }

        if include_split_times:
            params["includeSplitTimes"] = True

        resp = self._make_call(Endpoint.RESULTS, params, headers)
        return ResultList.from_xml(resp.content)

    def get_all_results_for_person(
        self,
        person_id: int,
        start_date: str,
        end_date: str,
        top: int = 0,
    ) -> ResultListList:
        """Get all results for a person.

        Args:
            person_id: ID of the persons to get results for.
            start_date: begin date for competitions
            end_date: end date for competitions
            top: also include the top n runners in each competition
                in the result list.

        Returns:
            ResultListList: All results for the searched person.
        """
        params: dict[str, Any] = {
            "fromDate": start_date,
            "toDate": end_date,
            "personId": person_id,
        }
        if top:
            params["top"] = top
        headers = {
            "ApiKey": self.api_token,
        }

        resp = self._make_call(
            Endpoint.PERSON_RESULTS,
            params,
            headers,
        )
        return ResultListList.from_xml(resp.content)

    def get_own_organization(self) -> Organisation:
        """Get the organization for the currently used API-Token.

        Returns:
            Organisation: The Organization that the TOKEN belongs to.
        """
        headers = {
            "ApiKey": self.api_token,
        }

        resp = self._make_call(Endpoint.TOKEN_ORGANIZATION, {}, headers)
        return Organisation.from_xml(resp.content)

    def get_all_persons_in_own_organization(self) -> Iterator[Person]:
        """Get all persons in the organization that the Token belongs to.

        Yields:
            All persons in the organization that the token belongs to.
        """
        org = self.get_own_organization()
        params: dict[str, Any] = {}
        headers = {
            "ApiKey": self.api_token,
        }

        resp = self._make_call(
            Endpoint.PERSONS,
            params,
            headers,
            extra_path=str(org.organisation_id),
        )
        all_persons = PersonList.from_xml(resp.content)
        yield from all_persons.persons

    @staticmethod
    def parse_distance(text: str) -> int:
        """Parse distance as displayed on Result pages in Eventor."""
        number = (
            (
                (parsy.digit.many() << parsy.whitespace).optional()
                + (parsy.digit.at_least(1) << parsy.string(" m,"))
            )
            .combine(lambda *txt: "".join(txt))
            .map(int)
        )
        return number.parse_partial(text)[0]

    def get_course_distances(self, event: EventRace) -> dict[str, int]:
        """Get the course distances for the event id.
            Don't uses the api but scrapes the result from the webpage.

        Args:
            event_id: The id of the event

        Returns: A dict that map course names to distances:
        """
        url = "https://eventor.orientering.se/Events/ResultList"
        params = {"eventID": event.event_id, "eventRaceId": event.race_id}
        resp = requests.get(url, params)
        resp.raise_for_status()
        distances = {}

        soup = BeautifulSoup(resp.text)
        divs = soup.findAll(class_="eventClassHeader")  # type: ignore[call-arg]
        for div in divs:
            inner_div = div.find("div")
            name = inner_div.h3.text.strip()
            inner_div.h3.decompose()
            distances[name] = self.parse_distance(inner_div.text)
        return distances
