import { BlogPost } from '../types'
import { howBetglitchWorks } from './how-betglitch-works'
import { valueBettingExplained } from './value-betting-explained'
import { transparentTrackRecords } from './transparent-track-records'

const posts: BlogPost[] = [
  howBetglitchWorks,
  valueBettingExplained,
  transparentTrackRecords,
]

export function getAllPosts(): BlogPost[] {
  return posts.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
}

export function getPostBySlug(slug: string): BlogPost | undefined {
  return posts.find(post => post.slug === slug)
}
