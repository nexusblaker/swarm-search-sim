import { TimelineEvent } from "@/components/mission/TimelineEvent";

export function EventTimeline({
  events,
}: {
  events: Array<Record<string, unknown>>;
}) {
  return (
    <div className="space-y-3">
      {events.map((event, index) => <TimelineEvent key={index} event={event} />)}
    </div>
  );
}
