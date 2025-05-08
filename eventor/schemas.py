"""Schemas for parsing xml responses from the API."""

from enum import IntEnum, auto
from pydantic_xml import BaseXmlModel, attr, element, wrapped


class ClassificationID(IntEnum):
    """Classification of different events."""

    CHAMPIONSHIP_EVENT = auto()
    NATIONAL_EVENT = auto()
    STATE_EVENT = auto()
    LOCAL_EVENT = auto()
    CLUB_EVENT = auto()


class Name(BaseXmlModel):
    """A model for a country name"""

    lang: str = attr("languageId")
    name: str


class Country(BaseXmlModel, tag="Country", search_mode="ordered"):
    """A model for a Country with an ID and multilanguage names."""

    country_id: int = wrapped("CountryId", attr("value"))
    names: list[Name] = element("Name")


class Date(BaseXmlModel):
    """A model for a date response."""

    date: str = element("Date")
    clock: str | None = element("Clock", default=None)


class Organisation(BaseXmlModel, search_mode="ordered"):
    """A model for an organisation."""

    organisation_id: int = element("OrganisationId")
    name: str = element("Name")
    short_name: str = element("ShortName")
    media_name: str | None = element("MediaName", default=None)
    organisation_type_id: int = element("OrganisationTypeId")
    country: Country | None = element("Country", default=None)
    parent_organization_id: int | None = wrapped(
        "ParentOrganisation/OrganisationId", default=None
    )


class OtherOrganisation(BaseXmlModel):
    """A model representing an unknown organization."""

    name: str = element("Name", default="Klubblös")


class Position(BaseXmlModel):
    """A model for a position."""

    x: float = attr()
    y: float = attr()
    unit: str = attr()


class EventRace(BaseXmlModel, search_mode="ordered"):
    """A Model for a race."""

    race_distance: str | None = attr("raceDistance", default=None)
    race_id: int = element("EventRaceId")
    event_id: int = element("EventId")
    name: str | None = element("Name", default=None)
    race_date: Date = element("RaceDate")
    event_position: Position | None = element(
        "EventCenterPosition", default=None
    )


class Event(BaseXmlModel, tag="Event", search_mode="ordered"):
    """A model for an Event."""

    event_id: int = element("EventId")
    name: str = element("Name")
    event_classification_id: int = element("EventClassificationId")
    event_status_id: int = element("EventStatusId")
    event_attribute_id: int | None = element("EventAttributeId", default=None)
    discipline_id: int | None = element("DisciplineId", default=None)
    start_date: str = wrapped("StartDate", element("Date"))
    finish_date: Date = element("FinishDate")
    organizer_ids: list[int] | None = wrapped(
        "Organiser",
        entity=element(tag="OrganisationId", default_factory=list),
        default=None,
    )
    event_races: list[EventRace] = element("EventRace")


class OrganisationList(BaseXmlModel):
    """A model for a list of Organizations."""

    organisations: list[Organisation] = element("Organisation")


class EventList(BaseXmlModel):
    """A model for a list of Events."""

    events: list[Event] = element("Event")


class Person(BaseXmlModel, search_mode="ordered"):
    sex: str | None = attr("sex", default=None)
    family_name: str = wrapped("PersonName/Family")
    first_name: str = wrapped("PersonName/Given")
    id: int = element("PersonId", default=None)
    birth_date: Date = element("BirthDate", default=None)
    nationality: Country = wrapped(
        "Nationality", element("Country", default=None)
    )

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.family_name}"


class PersonList(BaseXmlModel):
    """A model for a list of Persons."""

    persons: list[Person] = element("Person")


class Split(BaseXmlModel):
    """A model for a split-time in a race."""

    sequence: int = attr("sequence")
    control_code: int = element("ControlCode")
    time: str | None = element("Time", default=None)


class Result(BaseXmlModel, search_mode="ordered"):
    """A model for the results."""

    result_id: int = element("ResultId")
    start_time: Date = element("StartTime", default=None)
    finish_time: Date = element("FinishTime", default=None)
    time: str | None = element("Time", default=None)
    time_diff: str | None = element("TimeDiff", default=None)
    position: int | None = element("ResultPosition", default=None)
    status: str = wrapped("CompetitorStatus", attr("value"), default=None)
    punches: list[Split] = element("SplitTime", default_factory=list)


class RaceResult(BaseXmlModel, search_mode="ordered"):
    event_race_id: int = element("EventRaceId")
    result: Result = element("Result")


class PersonResult(BaseXmlModel, search_mode="ordered"):
    """A model for a result tied to a person."""

    person: Person = element("Person")
    organisation: Organisation | OtherOrganisation = element(
        "Organisation", default_factory=OtherOrganisation
    )
    result: Result | None = element("Result", default=None)
    race_result: RaceResult | None = element("RaceResult", default=None)


class ClassResult(BaseXmlModel, search_mode="ordered"):
    """A model for results for a whole class."""

    number_of_entries: int = attr("numberOfEntries")
    number_of_starts: int | None = attr("numberOfStarts", default=None)
    class_id: int = wrapped("EventClass/EventClassId")
    class_sex: str = wrapped("EventClass", attr("sex"))
    class_name: str = wrapped("EventClass/Name")
    class_short_name: str = wrapped("EventClass/ClassShortName")
    class_type_id: int = wrapped("EventClass/ClassTypeId")
    class_result: list[PersonResult] = element(
        "PersonResult", default_factory=list
    )


class ResultList(BaseXmlModel):
    """A model for results for an Event."""

    event: Event = element("Event")
    results: list[ClassResult] = element("ClassResult", default_factory=list)


class ResultListList(BaseXmlModel, search_mode="ordered"):
    """A model for a list of results for a series of events."""

    result_lists: list[ResultList] = element("ResultList", default_factory=list)
