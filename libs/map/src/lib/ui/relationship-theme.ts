import type { EventRelationshipType } from '@hermes/util-types';

export const RELATIONSHIP_COLORS: Record<EventRelationshipType, string> = {
  CAUSED: '#ffb454',
  FOLLOW_UP: '#00f0ff',
  REACTION: '#ff4fd8',
  RELATED: '#b388ff',
};

export const ACTOR_VECTOR_COLOR = '#e2f1ff';

export interface RelationshipLegendEntry {
  readonly key: EventRelationshipType | 'ACTOR';
  readonly label: string;
  readonly color: string;
  readonly dashed: boolean;
}

export const RELATIONSHIP_LEGEND_ITEMS: readonly RelationshipLegendEntry[] = [
  { key: 'CAUSED', label: 'CAUSED', color: RELATIONSHIP_COLORS.CAUSED, dashed: false },
  {
    key: 'FOLLOW_UP',
    label: 'FOLLOW UP',
    color: RELATIONSHIP_COLORS.FOLLOW_UP,
    dashed: false,
  },
  {
    key: 'REACTION',
    label: 'REACTION',
    color: RELATIONSHIP_COLORS.REACTION,
    dashed: false,
  },
  {
    key: 'RELATED',
    label: 'RELATED',
    color: RELATIONSHIP_COLORS.RELATED,
    dashed: false,
  },
  {
    key: 'ACTOR',
    label: 'ACTOR',
    color: ACTOR_VECTOR_COLOR,
    dashed: true,
  },
];

export function relationshipTypeColor(
  type: EventRelationshipType,
): string {
  return RELATIONSHIP_COLORS[type];
}
