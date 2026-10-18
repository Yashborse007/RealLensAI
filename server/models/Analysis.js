import mongoose from "mongoose";

const analysisSchema = new mongoose.Schema(
  {
    userId: {
      type: String,
      required: true,
      index: true,
    },
    mediaId: {
      type: String,
      required: true,
      index: true,
    },
    analysisId: {
      type: String,
      default: "",
      index: true,
    },
    mediaType: {
      type: String,
      enum: ["image", "video", "audio"],
      required: true,
    },
    filename: {
      type: String,
      required: true,
    },
    status: {
      type: String,
      enum: ["UPLOADED", "PROCESSING", "COMPLETED", "PARTIAL", "FAILED"],
      default: "UPLOADED",
      uppercase: true,
    },
    prediction: {
      type: String,
      enum: ["REAL", "FAKE", "UNCERTAIN"],
      default: "UNCERTAIN",
      uppercase: true,
    },
    confidence: {
      type: Number,
      default: 0,
      min: 0,
      max: 1,
    },
    quality: {
      type: String,
      enum: ["GOOD", "FAIR", "POOR", "UNKNOWN"],
      default: "UNKNOWN",
      uppercase: true,
    },
    qualityScore: {
      type: Number,
      default: 0,
      min: 0,
      max: 1,
    },
    qualityDetails: {
      type: Object,
      default: {},
    },
    qualityWarning: {
      type: String,
      default: "",
    },
    modalityScores: {
      type: Object,
      default: {},
    },
    modalities: {
      type: Object,
      default: {},
    },
    evidence: {
      type: [mongoose.Schema.Types.Mixed],
      default: [],
    },
    timestamps: {
      type: Object,
      default: {},
    },
    processing: {
      type: Object,
      default: {},
    },
    modelVersions: {
      type: Object,
      default: {},
    },
    facesDetected: {
      type: Number,
      default: 0,
    },
    suspiciousFrames: {
      type: Number,
      default: 0,
    },
    suspiciousTimestamps: {
      type: [String],
      default: [],
    },
    processingTime: {
      type: Number,
      default: 0,
    },
    modelVersion: {
      type: String,
      default: "AIDE",
    },
    reportPath: {
      type: String,
      default: "",
    },
    createdAt: {
      type: Date,
      default: Date.now,
    },
  },
  {
    timestamps: false,
  },
);

analysisSchema.set("toJSON", {
  virtuals: true,
  transform: (doc, ret) => {
    ret.id = String(doc._id || ret.id || doc.id);
    delete ret._id;
    delete ret.__v;
    return ret;
  },
});

const Analysis = mongoose.model("Analysis", analysisSchema);
export default Analysis;
