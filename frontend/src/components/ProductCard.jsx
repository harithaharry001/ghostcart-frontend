/**
 * Product Card Component
 *
 * Displays individual product with image, name, price, delivery, stock status.
 * User Story 1, Scenario 1: "displays 3 matching coffee makers with images,
 * names, prices around $69, and delivery estimates like '2 day delivery'"
 *
 * AP2 Compliance:
 * - Clear product information for informed purchase decisions
 * - Stock status visibility per FR-001
 */
import React from 'react';

export default function ProductCard({ product, onSelect, isSelected = false }) {
  const {
    product_id,
    name,
    description,
    category,
    price_cents,
    stock_status,
    delivery_estimate_days,
    image_url
  } = product;

  const priceInDollars = (price_cents / 100).toFixed(2);
  const isInStock = stock_status === 'in_stock';

  return (
    <div
      className={`bg-white border rounded-lg p-4 transition-all ${
        isSelected
          ? 'border-blue-500 bg-blue-50 shadow-md'
          : 'border-gray-200 hover:border-gray-300 hover:shadow-md'
      } ${!isInStock ? 'opacity-60' : ''}`}
    >
      {/* Product Image */}
      <div className="aspect-square bg-gray-100 rounded-md mb-3 flex items-center justify-center overflow-hidden">
        {image_url ? (
          <img
            src={image_url}
            alt={name}
            className="w-full h-full object-cover"
            onError={(e) => {
              // Fallback if image fails to load
              e.target.style.display = 'none';
              e.target.parentElement.innerHTML = '<div class="text-gray-400 text-4xl">📦</div>';
            }}
          />
        ) : (
          <div className="text-gray-400 text-4xl">📦</div>
        )}
      </div>

      {/* Category Badge */}
      {category && (
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
          {category}
        </div>
      )}

      {/* Product Name */}
      <h3 className="font-semibold text-gray-900 leading-tight mb-2">
        {name}
      </h3>

      {/* Description */}
      {description && (
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">
          {description}
        </p>
      )}

      {/* Price and Delivery - matching "prices around $69, and delivery estimates like '2 day delivery'" */}
      <div className="flex items-baseline justify-between mb-3">
        <div className="text-2xl font-bold text-gray-900">
          ${priceInDollars}
        </div>
        <div className="text-sm text-gray-600">
          {delivery_estimate_days} day delivery
        </div>
      </div>

      {/* Stock Status */}
      <div className="flex items-center gap-2 mb-3">
        {isInStock ? (
          <>
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-sm text-green-700 font-medium">In Stock</span>
          </>
        ) : (
          <>
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span className="text-sm text-red-700 font-medium">Out of Stock</span>
          </>
        )}
      </div>

      {/* Select Button */}
      <button
        onClick={() => onSelect(product)}
        disabled={!isInStock}
        className={`w-full py-2.5 px-4 rounded-md font-medium transition-colors ${
          isInStock
            ? isSelected
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-blue-500 text-white hover:bg-blue-600'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
      >
        {isSelected ? 'Selected ✓' : isInStock ? 'Select' : 'Unavailable'}
      </button>
    </div>
  );
}
