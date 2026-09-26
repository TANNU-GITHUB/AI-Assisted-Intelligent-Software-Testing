import { Hero } from '@/components/sections/Hero';
import { TestingJourney } from '@/components/sections/TestingJourney';
import { FeatureLab } from '@/components/sections/FeatureLab';
import { BugHunt } from '@/components/sections/BugHunt';
import { Stats } from '@/components/sections/Stats';
import { CTA } from '@/components/sections/CTA';
import { Footer } from '@/components/navigation/Footer';

export default function Home() {
  return (
    <>
      <Hero />
      <TestingJourney />
      <FeatureLab />
      <BugHunt />
      <Stats />
      <CTA />
      <Footer />
    </>
  );
}
