
export default function Loading() {
    return (
        <div className="min-h-screen bg-[#141414] text-white flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
                <div className="w-12 h-12 border-4 border-[#F7931A] border-t-transparent rounded-full animate-spin"></div>
                <p className="text-gray-400 animate-pulse">Loading Bitcoin Dashboard...</p>
            </div>
        </div>
    );
}
