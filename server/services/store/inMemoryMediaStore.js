/**
 * RealLens AI - In-Memory Media Store Fallback
 */

const mediaRecords = [];
const analysisRecords = [];

export const saveMediaRecord = async (data) => {
  const record = {
    ...data,
    uploadedAt: new Date().toISOString(),
  };
  mediaRecords.push(record);
  return record;
};

export const findMediaById = (mediaId) => {
  return mediaRecords.find((m) => m.mediaId === mediaId) || null;
};

export const saveAnalysisRecord = async (data) => {
  const record = {
    ...data,
    id:
      data.id ||
      data.analysisId ||
      data._id ||
      `ana_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
    analysisId:
      data.analysisId ||
      data.id ||
      data._id ||
      `ana_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
    createdAt: data.createdAt || new Date().toISOString(),
  };

  analysisRecords.push(record);
  return record;
};

export const findAnalysisById = (analysisId) => {
  return (
    analysisRecords.find(
      (item) =>
        item.id === analysisId ||
        item.analysisId === analysisId ||
        item.mediaId === analysisId ||
        item._id === analysisId,
    ) || null
  );
};

export const findAnalysesByUser = (userId) => {
  return analysisRecords.filter(
    (item) => String(item.userId || item.user || "") === String(userId),
  );
};

export const deleteAnalysisRecord = (userId, analysisId) => {
  const index = analysisRecords.findIndex((item) => {
    const matchId =
      item.id === analysisId ||
      item.analysisId === analysisId ||
      item.mediaId === analysisId ||
      item._id === analysisId;
    return matchId && String(item.userId || item.user || "") === String(userId);
  });

  if (index < 0) return null;
  const [deleted] = analysisRecords.splice(index, 1);
  return deleted;
};
