import type { Metadata } from "next";
import { fetchCampaign } from "@/lib/api";
import { shortText } from "@/lib/format";
import { CampaignClient } from "./CampaignClient";

const fallbackImage = "https://images.unsplash.com/photo-1488521787991-ed7bbaae773c";

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const campaign = await fetchCampaign(params.id);
  const description = shortText(campaign.description, 150);

  return {
    title: `${campaign.title} | TipForTea`,
    description,
    openGraph: {
      title: campaign.title,
      description,
      images: [campaign.cover_image_url || fallbackImage],
      type: "article",
    },
    twitter: {
      card: "summary_large_image",
      title: campaign.title,
      description,
      images: [campaign.cover_image_url || fallbackImage],
    },
  };
}

export default async function CampaignPage({ params }: { params: { id: string } }) {
  const campaign = await fetchCampaign(params.id);
  return <CampaignClient initialCampaign={campaign} />;
}
